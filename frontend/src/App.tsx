import { AppShell } from '@astryxdesign/core';
import { HomePage } from './HomePage';

function App() {
  return (
    <AppShell contentPadding={6} height="fill" variant="wash">
      <HomePage />
    </AppShell>
  );
}

export default App;
