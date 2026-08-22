import { Theme } from "@astryxdesign/core/theme";
import { neutralTheme } from "@astryxdesign/theme-neutral";
import type { ReactNode } from "react";

export function AppTheme({ children }: { children: ReactNode }) {
  return <Theme theme={neutralTheme}>{children}</Theme>;
}
