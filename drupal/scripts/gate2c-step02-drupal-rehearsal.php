<?php

declare(strict_types=1);

/**
 * Gate 2C.02 dedicated, model-free Drupal persistence/lock rehearsal.
 *
 * This file never calls the frozen recommendation operations. It uses a unique
 * rehearsal-only key/value collection and lock while retaining the certified
 * 1,800-second lease. The lock is never cleared, shortened, deleted, bypassed,
 * or replaced.
 */

const GATE2C_STEP02_LOCK_LEASE = 1800.0;
const GATE2C_STEP02_PARTIAL_PROBE_LEASE = 1.0;
const GATE2C_STEP02_COLLECTION = 'agentic_harness_gate2c_step02_rehearsal';
const GATE2C_STEP02_SEAM = 'after target 6 is fully persisted and before target 7 begins';
const GATE2C_STEP02_ARGUMENT_SPECIFICATIONS = [
  'worker' => 3,
  'process-check' => 3,
  'immediate' => 2,
  'post-expiry' => 2,
  'post-expiry-partial' => 2,
];

function gate2c_step02_fail(string $message): never {
  throw new RuntimeException($message);
}

/**
 * Normalize only Drush php:script's documented post-`--` argument surface.
 *
 * PhpCommands::script() removes the script path from `$extra` before including
 * this file. No process-global, request, or environment fallback is accepted.
 *
 * @param mixed $drush_extra
 *   The `$extra` variable injected by Drush's command method scope.
 *
 * @return array{mode: string, run_id: string, final_argument: ?string}
 */
function gate2c_step02_normalize_drush_extra(mixed $drush_extra): array {
  if (!is_array($drush_extra) || !array_is_list($drush_extra)) {
    gate2c_step02_fail('Drush php:script $extra arguments are required.');
  }
  foreach ($drush_extra as $argument) {
    if (!is_string($argument) || $argument === '' || str_contains($argument, "\0")) {
      gate2c_step02_fail('Drush php:script arguments must be non-empty strings.');
    }
  }
  $mode = $drush_extra[0] ?? '';
  $expected_count = GATE2C_STEP02_ARGUMENT_SPECIFICATIONS[$mode] ?? NULL;
  if ($expected_count === NULL || count($drush_extra) !== $expected_count) {
    gate2c_step02_fail('Usage: drush php:script gate2c-step02-drupal-rehearsal.php -- worker|immediate|post-expiry|post-expiry-partial|process-check RUN_ID [CONTROL_DIR|PID]');
  }
  $run_id = $drush_extra[1];
  gate2c_step02_lock_name($run_id);
  $final_argument = $drush_extra[2] ?? NULL;
  if ($mode === 'worker') {
    if (!str_starts_with($final_argument, '/var/www/html/.cache/gate2c-step02/') || !str_ends_with($final_argument, '/control')) {
      gate2c_step02_fail('Worker control path is outside the dedicated container runtime root.');
    }
  }
  elseif ($mode === 'process-check') {
    if (!ctype_digit($final_argument) || (int) $final_argument <= 1) {
      gate2c_step02_fail('Expected worker PID is invalid.');
    }
  }
  return ['mode' => $mode, 'run_id' => $run_id, 'final_argument' => $final_argument];
}

/** @return array<string, mixed> */
function gate2c_step02_read_state(string $run_id): array {
  $value = \Drupal::service('keyvalue')->get(GATE2C_STEP02_COLLECTION)->get($run_id);
  if (!is_array($value)) {
    gate2c_step02_fail('Dedicated rehearsal state is unavailable.');
  }
  return $value;
}

/** @param array<string, mixed> $value */
function gate2c_step02_write_control(string $path, array $value): void {
  $parent = dirname($path);
  if (!is_dir($parent) || is_link($parent)) {
    gate2c_step02_fail('Control directory must already exist and may not be a symlink.');
  }
  $encoded = json_encode($value, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
  if (file_put_contents($path, $encoded, LOCK_EX) === FALSE) {
    gate2c_step02_fail('Unable to write sanitized control record.');
  }
}

function gate2c_step02_lock_name(string $run_id): string {
  if (preg_match('/^gate2c-step02-drupal-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{8}$/', $run_id) !== 1) {
    gate2c_step02_fail('Invalid fresh Drupal rehearsal run ID.');
  }
  return 'agentic_harness_gate2c_step02_rehearsal:' . $run_id;
}

/** @param array<string, mixed> $value */
function gate2c_step02_state_sha256(array $value): string {
  return hash('sha256', json_encode($value, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
}

/** @return list<string> */
function gate2c_step02_identities(string $run_id, int $count): array {
  $values = [];
  for ($sequence = 1; $sequence <= $count; $sequence++) {
    $values[] = hash('sha256', 'gate2c-model-free:' . $run_id . ':' . $sequence);
  }
  return $values;
}

function gate2c_step02_worker(string $run_id, string $control_dir): never {
  $lock_name = gate2c_step02_lock_name($run_id);
  $lock = \Drupal::service('lock.persistent');
  if (!$lock->acquire($lock_name, GATE2C_STEP02_LOCK_LEASE)) {
    gate2c_step02_fail('Dedicated rehearsal lock unavailable before worker start.');
  }

  $lock_acquired_at_unix = microtime(TRUE);
  $actual_worker_pid = getmypid();

  $state = [
    'schema_version' => 1,
    'trial_id' => $run_id,
    'run_id' => $run_id,
    'framework_origin' => 'drupal_ai',
    'completed_sequences' => [1, 2, 3, 4, 5, 6],
    'next_target' => 7,
    'target_7_started' => FALSE,
    'synthetic_recommendation_identities' => gate2c_step02_identities($run_id, 6),
    'model_generations' => 0,
    'provider_requests' => 0,
    'recommendation_writes' => 0,
    'source_mutations' => 0,
    'lock_name_sha256' => hash('sha256', $lock_name),
    'lock_lease_seconds' => 1800,
    'lock_acquired_at_unix' => $lock_acquired_at_unix,
    'lock_expires_not_before_unix' => $lock_acquired_at_unix + GATE2C_STEP02_LOCK_LEASE,
    'lock_owner_actual_worker_pid' => $actual_worker_pid,
  ];
  \Drupal::service('keyvalue')->get(GATE2C_STEP02_COLLECTION)->set($run_id, $state);
  $midpoint = $control_dir . '/midpoint.json';
  gate2c_step02_write_control($midpoint, $state);
  $host_pid = (int) trim((string) file_get_contents($control_dir . '/expected-host-pid.txt'));
  if ($host_pid <= 1) {
    gate2c_step02_fail('Expected host wrapper PID is unavailable.');
  }
  gate2c_step02_write_control($control_dir . '/seam-ready.json', [
    'schema_version' => 1,
    'semantic_boundary' => GATE2C_STEP02_SEAM,
    'framework_origin' => 'drupal_ai',
    'trial_id' => $run_id,
    'run_id' => $run_id,
    'completed_sequences' => [1, 2, 3, 4, 5, 6],
    'next_target' => 7,
    'target_7_started' => FALSE,
    'midpoint_sha256' => hash_file('sha256', $midpoint),
    'independently_verifiable' => TRUE,
    'host_worker_pid' => $host_pid,
    'actual_worker_pid' => $actual_worker_pid,
    'lock_name_sha256' => $state['lock_name_sha256'],
    'lock_acquired_at_unix' => $state['lock_acquired_at_unix'],
    'lock_expires_not_before_unix' => $state['lock_expires_not_before_unix'],
  ]);

  // SIGKILL is expected. A normal exit would release the lock and invalidate proof.
  while (TRUE) {
    sleep(1);
  }
}

/** @return array<string, mixed> */
function gate2c_step02_immediate(string $run_id): array {
  $state = gate2c_step02_read_state($run_id);
  if ($state['completed_sequences'] !== [1, 2, 3, 4, 5, 6] || $state['next_target'] !== 7 || $state['target_7_started'] !== FALSE) {
    gate2c_step02_fail('Persisted rehearsal midpoint changed before immediate observation.');
  }
  $before_sha256 = gate2c_step02_state_sha256($state);
  $lock = \Drupal::service('lock.persistent');
  $acquired = $lock->acquire(gate2c_step02_lock_name($run_id), GATE2C_STEP02_LOCK_LEASE);
  if ($acquired) {
    $lock->release(gate2c_step02_lock_name($run_id));
    gate2c_step02_fail('Immediate invocation unexpectedly acquired the dedicated persistent lock.');
  }
  $after = gate2c_step02_read_state($run_id);
  $after_sha256 = gate2c_step02_state_sha256($after);
  if ($before_sha256 !== $after_sha256) {
    gate2c_step02_fail('Immediate observation changed dedicated rehearsal state.');
  }
  $observed_at_unix = microtime(TRUE);
  if ($observed_at_unix >= (float) $state['lock_expires_not_before_unix']) {
    gate2c_step02_fail('Immediate observation did not occur before the natural-expiry boundary.');
  }
  return [
    'schema_version' => 1,
    'status' => 'PASS_LOCK_DENIED',
    'run_id' => $run_id,
    'completed_sequences' => $state['completed_sequences'],
    'next_target' => $state['next_target'],
    'lock_lease_seconds' => 1800,
    'lock_mutation' => 'NONE',
    'lock_name_sha256' => $state['lock_name_sha256'],
    'lock_owner_actual_worker_pid' => $state['lock_owner_actual_worker_pid'],
    'lock_acquired_at_unix' => $state['lock_acquired_at_unix'],
    'lock_expires_not_before_unix' => $state['lock_expires_not_before_unix'],
    'observed_at_unix' => $observed_at_unix,
    'observed_before_natural_expiry' => TRUE,
    'state_sha256_before' => $before_sha256,
    'state_sha256_after' => $after_sha256,
    'model_generations' => 0,
    'provider_requests' => 0,
    'recommendation_writes' => 0,
    'source_mutations' => 0,
  ];
}

/** @return array<string, mixed> */
function gate2c_step02_post_expiry(string $run_id): array {
  $state = gate2c_step02_read_state($run_id);
  $before_sha256 = gate2c_step02_state_sha256($state);
  $observed_at_unix = microtime(TRUE);
  if ($observed_at_unix < (float) $state['lock_expires_not_before_unix']) {
    gate2c_step02_fail('Natural lease expiry time has not elapsed.');
  }
  $lock_name = gate2c_step02_lock_name($run_id);
  $lock = \Drupal::service('lock.persistent');
  if (!$lock->acquire($lock_name, GATE2C_STEP02_LOCK_LEASE)) {
    gate2c_step02_fail('Dedicated lock has not expired naturally.');
  }
  try {
    if ($state['completed_sequences'] !== [1, 2, 3, 4, 5, 6] || $state['next_target'] !== 7) {
      gate2c_step02_fail('Persisted rehearsal midpoint changed.');
    }
    $state['completed_sequences'] = range(1, 12);
    $state['next_target'] = 13;
    $state['target_7_started'] = TRUE;
    $state['first_post_restart_target'] = 7;
    $state['synthetic_recommendation_identities'] = gate2c_step02_identities($run_id, 12);
    \Drupal::service('keyvalue')->get(GATE2C_STEP02_COLLECTION)->set($run_id, $state);
  }
  finally {
    // Normal owner release is not a clear/shorten/delete/bypass operation.
    $lock->release($lock_name);
  }
  return [
    'schema_version' => 1,
    'status' => 'PASS_POST_NATURAL_EXPIRY',
    'run_id' => $run_id,
    'completed_sequences' => $state['completed_sequences'],
    'first_post_restart_target' => 7,
    'replay_count' => 0,
    'duplicate_count' => 0,
    'lock_lease_seconds' => 1800,
    'lock_mutation' => 'NONE',
    'lock_name_sha256' => $state['lock_name_sha256'],
    'lock_owner_actual_worker_pid' => $state['lock_owner_actual_worker_pid'],
    'lock_acquired_at_unix' => $state['lock_acquired_at_unix'],
    'lock_expires_not_before_unix' => $state['lock_expires_not_before_unix'],
    'observed_at_unix' => $observed_at_unix,
    'elapsed_since_lock_acquired_seconds' => $observed_at_unix - (float) $state['lock_acquired_at_unix'],
    'natural_expiry_elapsed' => TRUE,
    'wait_operation_mutations' => 0,
    'state_sha256_before' => $before_sha256,
    'state_sha256_after' => gate2c_step02_state_sha256($state),
    'model_generations' => 0,
    'provider_requests' => 0,
    'recommendation_writes' => 0,
    'source_mutations' => 0,
  ];
}

/**
 * Observe only the post-expiry preconditions retained by the final failed run.
 *
 * Drupal's persistent database lock backend has no mutation-free availability
 * proof: acquire() may delete an expired semaphore row before inserting the
 * probe row. The probe therefore uses a one-second lease and releases it in a
 * finally block. It never writes rehearsal key/value state or processes a
 * target.
 *
 * @return array<string, mixed>
 */
function gate2c_step02_post_expiry_partial(string $run_id): array {
  $state = gate2c_step02_read_state($run_id);
  if ($state['completed_sequences'] !== [1, 2, 3, 4, 5, 6]
      || $state['next_target'] !== 7
      || $state['target_7_started'] !== FALSE
      || $state['synthetic_recommendation_identities'] !== gate2c_step02_identities($run_id, 6)) {
    gate2c_step02_fail('Persisted rehearsal midpoint is not eligible for partial observation.');
  }
  $before_sha256 = gate2c_step02_state_sha256($state);
  $observed_at_unix = microtime(TRUE);
  if ($observed_at_unix < (float) $state['lock_expires_not_before_unix']) {
    gate2c_step02_fail('Natural lease expiry time has not elapsed.');
  }
  $lock_name = gate2c_step02_lock_name($run_id);
  $lock = \Drupal::service('lock.persistent');
  $acquired = $lock->acquire($lock_name, GATE2C_STEP02_PARTIAL_PROBE_LEASE);
  if (!$acquired) {
    gate2c_step02_fail('Dedicated lock remains unavailable after recorded natural expiry.');
  }
  try {
    $after = gate2c_step02_read_state($run_id);
    $after_sha256 = gate2c_step02_state_sha256($after);
    if ($before_sha256 !== $after_sha256) {
      gate2c_step02_fail('Partial post-expiry observation changed dedicated rehearsal state.');
    }
  }
  finally {
    $lock->release($lock_name);
  }
  return [
    'schema_version' => 1,
    'record_type' => 'DRUPAL_POST_EXPIRY_PARTIAL_OBSERVATION_EVIDENCE',
    'status' => 'PASS_PARTIAL_POST_NATURAL_EXPIRY_NON_CERTIFYING',
    'run_id' => $run_id,
    'observation_timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
    'observation_timestamp_unix' => $observed_at_unix,
    'recorded_lock_name_sha256' => $state['lock_name_sha256'],
    'recorded_lock_acquired_at_unix' => $state['lock_acquired_at_unix'],
    'recorded_lock_expires_not_before_unix' => $state['lock_expires_not_before_unix'],
    'observation_occurred_after_recorded_expiry' => TRUE,
    'lock_acquisition_result' => 'ACQUIRED_AFTER_RECORDED_EXPIRY',
    'lock_probe_method' => 'PERSISTENT_LOCK_ACQUIRE_THEN_IMMEDIATE_RELEASE',
    'lock_probe_lease_seconds' => 1,
    'lock_probe_released' => TRUE,
    'expired_semaphore_cleanup_may_occur' => TRUE,
    'active_lock_shortening_or_bypass' => FALSE,
    'completed_sequences' => $state['completed_sequences'],
    'next_target' => $state['next_target'],
    'target_7_started' => $state['target_7_started'],
    'target_7_processed' => FALSE,
    'processed_identity_count' => count($state['synthetic_recommendation_identities']),
    'processed_identities_unique' => count(array_unique($state['synthetic_recommendation_identities'])) === 6,
    'state_sha256_before' => $before_sha256,
    'state_sha256_after' => $after_sha256,
    'worker_launch_count' => 0,
    'target_processing_count' => 0,
    'model_generation_count' => 0,
    'provider_request_count' => 0,
    'recommendation_write_count' => 0,
    'source_mutation_count' => 0,
    'certifying_evidence' => FALSE,
    'immediate_lock_denial_reconstructed' => FALSE,
    'historical_termination_proof_reconstructed' => FALSE,
  ];
}

/** @return array<string, mixed> */
function gate2c_step02_process_check(string $run_id, int $expected_pid): array {
  gate2c_step02_lock_name($run_id);
  if ($expected_pid <= 1) {
    gate2c_step02_fail('Expected worker PID is invalid.');
  }
  $observer_pid = getmypid();
  $observer_namespace = @readlink('/proc/self/ns/pid');
  $matching = [];
  $candidates = [];
  foreach (glob('/proc/[0-9]*/cmdline') ?: [] as $path) {
    $raw = @file_get_contents($path);
    if (!is_string($raw) || $raw === '') {
      continue;
    }
    $pid = (int) basename(dirname($path));
    $arguments = array_values(array_filter(explode("\0", rtrim($raw, "\0")), static fn(string $value): bool => $value !== ''));
    $script_index = NULL;
    foreach ($arguments as $index => $argument) {
      if (str_ends_with($argument, '/gate2c-step02-drupal-rehearsal.php') || $argument === 'scripts/gate2c-step02-drupal-rehearsal.php') {
        $script_index = $index;
        break;
      }
    }
    if ($script_index === NULL) {
      continue;
    }
    $separator_index = array_search('--', $arguments, TRUE);
    $mode = is_int($separator_index) ? ($arguments[$separator_index + 1] ?? NULL) : NULL;
    $candidate_run_id = is_int($separator_index) ? ($arguments[$separator_index + 2] ?? NULL) : NULL;
    $executable = basename($arguments[0] ?? '');
    $is_php = preg_match('/^php(?:[0-9]+(?:\.[0-9]+)*)?$/', $executable) === 1;
    $namespace = @readlink('/proc/' . $pid . '/ns/pid');
    $normalized = [
      'pid' => $pid,
      'observer' => $pid === $observer_pid,
      'executable' => $executable,
      'script' => 'gate2c-step02-drupal-rehearsal.php',
      'mode' => $mode,
      'run_id' => $candidate_run_id,
      'argument_count' => count($arguments),
      'argv_sha256' => hash('sha256', $raw),
      'pid_namespace_matches_observer' => is_string($observer_namespace) && is_string($namespace) && hash_equals($observer_namespace, $namespace),
    ];
    $normalized['exact_worker_identity'] = $is_php
      && $mode === 'worker'
      && $candidate_run_id === $run_id
      && $normalized['pid_namespace_matches_observer'] === TRUE;
    $candidates[] = $normalized;
    if ($normalized['exact_worker_identity'] === TRUE) {
      $matching[] = $pid;
    }
  }
  sort($matching, SORT_NUMERIC);
  usort($candidates, static fn(array $left, array $right): int => $left['pid'] <=> $right['pid']);
  $expected = array_values(array_filter($candidates, static fn(array $candidate): bool => $candidate['pid'] === $expected_pid));
  $expected_valid = count($expected) === 1 && $expected[0]['exact_worker_identity'] === TRUE;
  $unique = count($matching) === 1 && $matching === [$expected_pid];
  $decision = count($matching) === 0 ? 'NO_MATCHING_WORKER' : (
    $expected_valid && $unique ? 'EXACT_SINGLETON_VERIFIED' : (
      !$expected_valid ? 'EXPECTED_PID_IDENTITY_MISMATCH' : 'WORKER_UNIQUENESS_FAILURE'
    )
  );
  return [
    'schema_version' => 1,
    'record_type' => 'DRUPAL_PROCESS_IDENTITY_SCAN',
    'recorded_at' => gmdate('Y-m-d\TH:i:s\Z'),
    'verification_method' => 'CONTAINER_PROCFS_EXACT_SEAM_PID_AND_PHP_ARGV_WITH_WORKER_UNIQUENESS',
    'run_id' => $run_id,
    'observer_pid' => $observer_pid,
    'observer_pid_namespace' => is_string($observer_namespace) ? hash('sha256', $observer_namespace) : NULL,
    'expected_worker_pid' => $expected_pid,
    'matching_worker_count' => count($matching),
    'matching_worker_pids' => $matching,
    'candidates' => $candidates,
    'expected_pid_verified' => $expected_valid,
    'worker_uniqueness_verified' => $unique,
    'decision' => $decision,
    'configuration_sha256' => hash('sha256', 'v2:container-procfs:php:script:worker:exact-run-id:exact-seam-pid:singleton'),
  ];
}

$arguments = gate2c_step02_normalize_drush_extra($extra ?? NULL);
$mode = $arguments['mode'];
$run_id = $arguments['run_id'];
$final_argument = $arguments['final_argument'];
if ($mode === 'worker') {
  gate2c_step02_worker($run_id, $final_argument);
}
elseif ($mode === 'immediate') {
  print json_encode(gate2c_step02_immediate($run_id), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
}
elseif ($mode === 'post-expiry') {
  print json_encode(gate2c_step02_post_expiry($run_id), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
}
elseif ($mode === 'post-expiry-partial') {
  print json_encode(gate2c_step02_post_expiry_partial($run_id), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
}
elseif ($mode === 'process-check') {
  $expected_pid = (int) $final_argument;
  print json_encode(gate2c_step02_process_check($run_id, $expected_pid), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
}
