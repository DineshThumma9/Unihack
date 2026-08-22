from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Literal
import pandas as pd

from jobs.models import JobResult, JobStatus, ProductRunResult
from preprocess import preprocess
from main import build_graph, State


async def process_product(
    graph: Any,
    row: pd.Series | dict,
    index: int,
) -> ProductRunResult:
    product_start = perf_counter()
    row_dict = row.to_dict() if isinstance(row, pd.Series) else row
    mpn = str(row_dict.get("Mfg_Part_Num", f"PRODUCT_{index}"))

    try:
        state: State = {
            "row": row_dict,
            "retry_count": 0,
        }
        result = await graph.ainvoke(state)
        product_time = perf_counter() - product_start

        validation = result.get("validation", {})
        failed_rules = [rule for rule, passed in validation.items() if not passed]
        total_rules = len(validation)
        passed_rules = sum(1 for passed in validation.values() if passed)
        validation_score = (passed_rules / total_rules * 100.0) if total_rules > 0 else 100.0

        product_obj = result.get("product")
        manufacturer = None
        brand = None
        attributes_found = 0

        if product_obj:
            if hasattr(product_obj, "identity") and product_obj.identity:
                manufacturer = product_obj.identity.manufacturer_name
                brand = product_obj.identity.brand_name
            if hasattr(product_obj, "attributes") and product_obj.attributes:
                if hasattr(product_obj.attributes, "custom_attributes"):
                    attributes_found = len(product_obj.attributes.custom_attributes)

        status: Literal["success", "warning", "failed"] = (
            "warning" if failed_rules else "success"
        )

        return ProductRunResult(
            index=index,
            mpn=mpn,
            status=status,
            validation=validation,
            validation_score=validation_score,
            manufacturer=manufacturer,
            brand=brand,
            attributes_found=attributes_found,
            processing_time=product_time,
            needs_review=bool(failed_rules),
            error=None,
            delivery_row=result.get("delivery_row"),
        )
    except Exception as exc:
        product_time = perf_counter() - product_start
        return ProductRunResult(
            index=index,
            mpn=mpn,
            status="failed",
            validation={},
            validation_score=0.0,
            manufacturer=None,
            brand=None,
            attributes_found=0,
            processing_time=product_time,
            needs_review=True,
            error=f"{type(exc).__name__}: {exc}",
            delivery_row=None,
        )


async def run_job(
    job_id: str,
    input_path: str,
    output_path: str,
    event_publisher: Any | None = None,
    job_manager: Any | None = None,
    product_concurrency: int = 2,
    limit: int | None = None,
) -> JobResult:
    total_start = perf_counter()

    try:
        df = preprocess(input_path)
        if limit is not None:
            df = df.head(limit)
        total_products = len(df)

        if event_publisher:
            await event_publisher.publish(
                job_id,
                {
                    "type": "job.started",
                    "job_id": job_id,
                    "total": total_products,
                },
            )

        graph = build_graph()
        semaphore = asyncio.Semaphore(product_concurrency)
        results: list[dict | None] = [None] * total_products

        processed_count = 0
        successful_count = 0
        warnings_count = 0
        failed_count = 0

        async def worker(index: int, row: pd.Series):
            nonlocal processed_count, successful_count, warnings_count, failed_count
            async with semaphore:
                if job_manager:
                    j = job_manager.get_job(job_id)
                    if j and j.status == JobStatus.CANCELLED:
                        return None

                mpn = str(row.get("Mfg_Part_Num", f"PRODUCT_{index}"))
                if event_publisher:
                    await event_publisher.publish(
                        job_id,
                        {
                            "type": "product.started",
                            "index": index,
                            "mpn": mpn,
                        },
                    )

                res = await process_product(graph, row, index)
                if job_manager:
                    job_manager.save_product_result(job_id, res)
                processed_count += 1

                if res.status == "success":
                    successful_count += 1
                elif res.status == "warning":
                    warnings_count += 1
                else:
                    failed_count += 1

                if res.delivery_row:
                    results[index] = res.delivery_row

                if event_publisher:
                    if res.status == "failed":
                        await event_publisher.publish(
                            job_id,
                            {
                                "type": "product.failed",
                                "index": index,
                                "mpn": mpn,
                                "error": res.error or "Unknown product error",
                            },
                        )
                    else:
                        await event_publisher.publish(
                            job_id,
                            {
                                "type": "product.completed",
                                "index": index,
                                "mpn": mpn,
                                "status": res.status,
                                "manufacturer": res.manufacturer,
                                "brand": res.brand,
                                "attributes_found": res.attributes_found,
                                "validation_passed": len([v for v in res.validation.values() if not v]) == 0,
                                "processing_time": round(res.processing_time, 2),
                            },
                        )

                return res

        tasks = [
            asyncio.create_task(worker(idx, row))
            for idx, (_, row) in enumerate(df.iterrows())
        ]
        product_results = await asyncio.gather(*tasks)

        # Write output CSV preserving original ordering
        valid_rows = [r for r in results if r is not None]
        if valid_rows:
            output_df = pd.DataFrame(valid_rows)
            output_df.to_csv(output_path, index=False)
        else:
            # Create empty CSV file if no valid rows
            with open(output_path, "w") as f:
                f.write("")

        job_res = JobResult(
            job_id=job_id,
            total=total_products,
            processed=processed_count,
            successful=successful_count,
            warnings=warnings_count,
            failed=failed_count,
            output_path=output_path,
            error=None,
        )

        if event_publisher:
            await event_publisher.publish(
                job_id,
                {
                    "type": "job.completed",
                    "job_id": job_id,
                    "total": total_products,
                    "processed": processed_count,
                    "successful": successful_count,
                    "warnings": warnings_count,
                    "failed": failed_count,
                    "output_ready": True,
                },
            )

        return job_res

    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        if event_publisher:
            await event_publisher.publish(
                job_id,
                {
                    "type": "job.failed",
                    "job_id": job_id,
                    "error": err_msg,
                },
            )
        return JobResult(
            job_id=job_id,
            total=0,
            processed=0,
            successful=0,
            warnings=0,
            failed=0,
            output_path=None,
            error=err_msg,
        )
