<?php

declare(strict_types=1);

use Drupal\ai\Event\PreGenerateResponseEvent;
use Drupal\ai_agents\Event\AgentRequestEvent;
use Drupal\user\UserInterface;

const GATE1_STEP07_STATE_COLLECTION = 'agentic_harness_drupal_ai.run_state';
const GATE1_STEP07_STATE_KEY = 'batch.active';
const GATE1_STEP07_ARTIFACT_KEY = 'batch.artifacts';

/** @var array<int, mixed> $extra */
$arguments = is_array($extra ?? NULL) ? $extra : [];
$mode = (string) ($arguments[0] ?? '');

function gate1_step07_emit(array $value): void {
  print json_encode($value, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR) . PHP_EOL;
}

function gate1_step07_user(string $name): UserInterface {
  $matches = \Drupal::entityTypeManager()->getStorage('user')->loadByProperties(['name' => $name]);
  $account = reset($matches);
  if (!$account instanceof UserInterface) {
    throw new RuntimeException('Required account unavailable: ' . $name);
  }
  return $account;
}

function gate1_step07_adapter(string $plugin_id, string $input_name, mixed $input): array {
  $plugin = \Drupal::service('plugin.manager.ai.function_calls')->createInstance($plugin_id);
  $plugin->setContextValue($input_name, $input);
  $plugin->execute();
  $result = $plugin->getStructuredOutput();
  if (!is_array($result) || ($result['ok'] ?? NULL) !== TRUE || !is_array($result['data'] ?? NULL)) {
    throw new RuntimeException('Certification adapter failed: ' . $plugin_id);
  }
  return $result['data'];
}

function gate1_step07_runtime(): array {
  $collection = \Drupal::service('keyvalue')->get(GATE1_STEP07_STATE_COLLECTION);
  $state = $collection->get(GATE1_STEP07_STATE_KEY);
  $artifacts = $collection->get(GATE1_STEP07_ARTIFACT_KEY);
  if (!is_array($state) || !is_array($artifacts) || ($state['status'] ?? NULL) !== 'completed') {
    throw new RuntimeException('Completed Drupal AI batch state is unavailable.');
  }
  return [$state, $artifacts];
}

function gate1_step07_block_model_calls(int &$provider, int &$agent): void {
  $dispatcher = \Drupal::service('event_dispatcher');
  $dispatcher->addListener(PreGenerateResponseEvent::EVENT_NAME, static function () use (&$provider): void {
    $provider++;
    throw new RuntimeException('Provider request prohibited during Step 1.07 replay/status certification.');
  }, 10000);
  $dispatcher->addListener(AgentRequestEvent::EVENT_NAME, static function () use (&$agent): void {
    $agent++;
    throw new RuntimeException('Agent request prohibited during Step 1.07 replay/status certification.');
  }, 10000);
}

function gate1_step07_replay(): array {
  [$state, $artifacts] = gate1_step07_runtime();
  $provider = 0;
  $agent = 0;
  gate1_step07_block_model_calls($provider, $agent);
  $current = \Drupal::service('current_user');
  $original = $current->getAccount();
  $records = [];
  try {
    $current->setAccount(gate1_step07_user('agent_bot'));
    foreach ($artifacts['recommendations'] ?? [] as $item) {
      $sequence = (int) ($item['sequence'] ?? 0);
      $recommendation = $item['recommendation'] ?? NULL;
      $original_submission = $artifacts['submissions'][$sequence - 1] ?? NULL;
      if (!is_array($recommendation) || !is_array($original_submission)) {
        throw new RuntimeException('Replay evidence is incomplete at sequence ' . $sequence);
      }
      $replay = gate1_step07_adapter('submit_recommendation', 'recommendation', $recommendation);
      foreach (['node_id', 'uuid', 'revision_id'] as $key) {
        if (($replay[$key] ?? NULL) !== ($original_submission[$key] ?? NULL)) {
          throw new RuntimeException('Replay identity changed at sequence ' . $sequence . ': ' . $key);
        }
      }
      $records[] = [
        'sequence' => $sequence,
        'node_id' => $replay['node_id'],
        'uuid' => $replay['uuid'],
        'revision_id' => $replay['revision_id'],
        'same_identity' => TRUE,
      ];
    }
  }
  finally {
    $current->setAccount($original);
  }
  return [
    'schema_version' => 1,
    'status' => 'pass',
    'run_id' => $state['run_id'],
    'replayed_count' => count($records),
    'duplicate_count' => 0,
    'provider_request_count' => $provider,
    'agent_request_count' => $agent,
    'records' => $records,
  ];
}

function gate1_step07_status_all(): array {
  [$state, $artifacts] = gate1_step07_runtime();
  $provider = 0;
  $agent = 0;
  gate1_step07_block_model_calls($provider, $agent);
  $current = \Drupal::service('current_user');
  $original = $current->getAccount();
  $records = [];
  try {
    $current->setAccount(gate1_step07_user('agent_bot'));
    foreach ($artifacts['submissions'] ?? [] as $submission) {
      $status = gate1_step07_adapter('get_recommendation_status', 'recommendation_id', (string) $submission['uuid']);
      if (($status['status'] ?? NULL) !== 'pending') {
        throw new RuntimeException('Certification status is not pending for ' . $submission['uuid']);
      }
      $records[] = [
        'uuid' => $status['uuid'],
        'revision_id' => $status['revision_id'],
        'status' => $status['status'],
      ];
    }
  }
  finally {
    $current->setAccount($original);
  }
  return [
    'schema_version' => 1,
    'status' => 'pass',
    'run_id' => $state['run_id'],
    'status_count' => count($records),
    'pending_count' => count($records),
    'provider_request_count' => $provider,
    'agent_request_count' => $agent,
    'records' => $records,
  ];
}

try {
  $result = match ($mode) {
    'replay' => gate1_step07_replay(),
    'status-all' => gate1_step07_status_all(),
    default => throw new InvalidArgumentException('Usage: replay | status-all'),
  };
  gate1_step07_emit($result);
}
catch (Throwable $exception) {
  fwrite(STDERR, sprintf("[ERROR] %s: %s\n", $exception::class, $exception->getMessage()));
  exit(1);
}
