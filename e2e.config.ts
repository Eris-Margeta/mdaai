import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';

// No model/providers/agents; deterministic browser operations only.
process.env.E2E_TELEMETRY_DISABLED = '1';
process.env.DO_NOT_TRACK = '1';
export default {
  targets: [{ name: 'chromium', engine: web(), app: { url: process.env.E2E_BASE_URL || 'http://127.0.0.1:8765' } }],
  workers: 4,
  retries: 0,
  timeout: 45000,
  assertionTimeout: 4000,
  output: process.env.E2E_OUTPUT || 'PROJECT-INTERNAL/e2e-local',
  reporters: ['list', 'markdown'],
} satisfies E2EConfig;
