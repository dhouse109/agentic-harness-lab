<?php

declare(strict_types=1);

use Drupal\ai\Dto\StructuredOutputSchema;
use Drupal\ai\Event\AiExceptionEvent;
use Drupal\ai\Event\PreGenerateResponseEvent;
use Drupal\ai\OperationType\Chat\ChatInput;
use Drupal\agentic_harness_drupal_ai\Service\FileEntityResolver;
use Drupal\ai_agents\Event\AgentRequestEvent;
use Drupal\ai_agents\Event\AgentResponseEvent;
use Drupal\ai_agents\Task\Task;
use Drupal\Core\Config\Entity\ConfigEntityInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;
use OpenAI\Exceptions\RateLimitException;
use Psr\Http\Message\ResponseInterface;

/**
 * Gate 1 Step 1.05 Drupal AI 12-target batch runner.
 *
 * Step 1.05 intentionally stops before human review. It proves the frozen
 * 12-target sequence, one model request per target, framework-owned persisted
 * state, deterministic failure after sequence 6, resume at sequence 7, zero
 * duplicate recommendations, and twelve pending review records.
 */

const GATE1_STEP05_MODEL = 'gpt-4.1-mini-2025-04-14';
const GATE1_STEP05_PROVIDER = 'openai';
const GATE1_STEP05_TEMPERATURE = 0.0;
const GATE1_STEP05_PROMPT_VERSION = 'drupal-ai-alt-text-v1.0.0';
const GATE1_STEP05_VALIDATOR_VERSION = 'gate05-validator-1.0.0';
const GATE1_STEP05_TARGET_SHA256 = '1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728';
const GATE1_STEP05_SOURCE_SHA256 = 'f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17';
const GATE1_STEP05_STATE_COLLECTION = 'agentic_harness_drupal_ai.run_state';
const GATE1_STEP05_STATE_KEY = 'batch.active';
const GATE1_STEP05_ARTIFACT_KEY = 'batch.artifacts';
const GATE1_STEP05_LOCK = 'agentic_harness_drupal_ai.batch';
const GATE1_STEP05_AGENT_ID = 'agentic_harness_alt_text_batch';
const GATE1_STEP05_TEMPLATE_AGENT_ID = 'content_type_agent_triage';
const GATE1_STEP05_FAILURE_AFTER_SEQUENCE = 6;
const GATE1_STEP05_RESUME_SEQUENCE = 7;
const GATE1_STEP05_TARGET_COUNT = 12;
const GATE1_STEP05_MODERATION_PACING_SECONDS = 65;

/** @var array<int, mixed> $extra */
$arguments = is_array($extra ?? NULL) ? $extra : [];
$mode = (string) ($arguments[0] ?? '');
$run_id_argument = (string) ($arguments[1] ?? '');

function gate1_step05_emit(array $value): void {
  print json_encode(
    $value,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ) . PHP_EOL;
}

function gate1_step05_now(): string {
  return gmdate('Y-m-d\TH:i:s\Z');
}

function gate1_step05_sort(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate1_step05_sort', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate1_step05_sort($item);
  }
  return $value;
}

function gate1_step05_json(mixed $value): string {
  return json_encode(
    gate1_step05_sort($value),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );
}

function gate1_step05_sha(mixed $value): string {
  return hash('sha256', gate1_step05_json($value));
}

function gate1_step05_file_resolver(): FileEntityResolver {
  $container = \Drupal::getContainer();
  return new FileEntityResolver(
    $container->get('entity_type.manager'),
    $container->get('file_system'),
  );
}

function gate1_step05_user(string $name): UserInterface {
  $matches = \Drupal::entityTypeManager()->getStorage('user')->loadByProperties(['name' => $name]);
  $account = reset($matches);
  if (!$account instanceof UserInterface) {
    throw new RuntimeException('Required account is unavailable: ' . $name);
  }
  return $account;
}

/**
 * Runs one installed FunctionCall adapter through its plugin manager.
 *
 * @return array<string, mixed>
 */
function gate1_step05_adapter(string $plugin_id, ?string $input_name = NULL, mixed $input = NULL): array {
  $plugin = \Drupal::service('plugin.manager.ai.function_calls')->createInstance($plugin_id);
  if ($input_name !== NULL) {
    $plugin->setContextValue($input_name, $input);
  }
  $plugin->execute();
  $output = $plugin->getStructuredOutput();
  if (!is_array($output) || ($output['ok'] ?? NULL) !== TRUE || !is_array($output['data'] ?? NULL)) {
    $code = is_array($output) ? ($output['error']['code'] ?? 'ADAPTER_FAILED') : 'ADAPTER_FAILED';
    throw new RuntimeException(sprintf('Adapter %s failed: %s', $plugin_id, $code));
  }
  return $output;
}

/**
 * @return array<int, array<string, mixed>>
 */
function gate1_step05_discover_targets(): array {
  $data = gate1_step05_adapter('discover_targets')['data'];
  if (
    array_is_list($data)
    || !array_key_exists('targets', $data)
    || !array_key_exists('total_count', $data)
    || !is_array($data['targets'])
    || !array_is_list($data['targets'])
    || !is_int($data['total_count'])
  ) {
    throw new RuntimeException('Discovery adapter data does not match the frozen envelope.');
  }
  $targets = $data['targets'];
  if ($data['total_count'] !== count($targets)) {
    throw new RuntimeException('Discovery adapter total_count differs from its target list.');
  }
  if (count($targets) !== GATE1_STEP05_TARGET_COUNT) {
    throw new RuntimeException('Discovery did not return exactly twelve frozen targets.');
  }
  foreach ($targets as $index => $target) {
    if (($target['sequence'] ?? NULL) !== $index + 1) {
      throw new RuntimeException('Discovery target ordering differs from frozen sequence.');
    }
  }
  if (gate1_step05_sha($targets) !== GATE1_STEP05_TARGET_SHA256) {
    throw new RuntimeException('Discovery target-sequence hash differs from the frozen contract.');
  }
  return $targets;
}

/**
 * Returns the current sanitized Drupal projection.
 *
 * @return array<string, mixed>
 */
function gate1_step05_snapshot(): array {
  $container = \Drupal::getContainer();
  $storage = $container->get('entity_type.manager')->getStorage('node');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->sort('nid', 'ASC')
    ->execute();

  $articles = [];
  foreach ($storage->loadMultiple($ids) as $node) {
    if (!$node instanceof NodeInterface) {
      continue;
    }
    $images = [];
    foreach ($node->get('field_image') as $delta => $item) {
      $file = $item->entity;
      $images[] = [
        'delta' => (int) $delta,
        'file_uuid' => $file instanceof FileInterface ? $file->uuid() : NULL,
        'alt' => (string) ($item->alt ?? ''),
        'title' => (string) ($item->title ?? ''),
      ];
    }
    $articles[] = [
      'node_uuid' => $node->uuid(),
      'revision_id' => (int) $node->getRevisionId(),
      'title' => (string) $node->label(),
      'status' => (bool) $node->isPublished(),
      'images' => $images,
    ];
  }

  $suggestion_count = (int) $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'alt_text_suggestion')
    ->count()
    ->execute();

  $current_user = $container->get('current_user');
  $original = $current_user->getAccount();
  try {
    $current_user->setAccount(gate1_step05_user('agent_bot'));
    $targets = $container->get('agentic_harness_tools.image_review_finder')->find();
  }
  finally {
    $current_user->setAccount($original);
  }

  $collection = $container->get('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);
  $state = $collection->get(GATE1_STEP05_STATE_KEY);
  $artifacts = $collection->get(GATE1_STEP05_ARTIFACT_KEY);
  $agent_present = $container->get('entity_type.manager')
    ->getStorage('ai_agent')
    ->load(GATE1_STEP05_AGENT_ID) instanceof ConfigEntityInterface;

  $target_hash = gate1_step05_sha($targets);
  $source_hash = gate1_step05_sha($articles);

  return [
    'schema_version' => 1,
    'article_count' => count($articles),
    'suggestion_count' => $suggestion_count,
    'target_count' => count($targets),
    'canonical_target_sequence' => $targets[0]['sequence'] ?? NULL,
    'target_sequence_sha256' => $target_hash,
    'article_source_sha256' => $source_hash,
    'runtime_state_present' => is_array($state),
    'runtime_artifacts_present' => is_array($artifacts),
    'runtime_status' => is_array($state) ? ($state['status'] ?? NULL) : NULL,
    'next_target_index' => is_array($state) ? ($state['next_target_index'] ?? NULL) : NULL,
    'temporary_agent_config_present' => $agent_present,
    'seeded_clean' => count($articles) === 20
      && $suggestion_count === 0
      && count($targets) === GATE1_STEP05_TARGET_COUNT
      && ($targets[0]['sequence'] ?? NULL) === 1
      && $target_hash === GATE1_STEP05_TARGET_SHA256
      && $source_hash === GATE1_STEP05_SOURCE_SHA256
      && !is_array($state)
      && !is_array($artifacts)
      && !$agent_present,
    'batch_completed_pending_review' => count($articles) === 20
      && $suggestion_count === GATE1_STEP05_TARGET_COUNT
      && count($targets) === GATE1_STEP05_TARGET_COUNT
      && $target_hash === GATE1_STEP05_TARGET_SHA256
      && $source_hash === GATE1_STEP05_SOURCE_SHA256
      && is_array($state)
      && ($state['status'] ?? NULL) === 'completed'
      && ($state['next_target_index'] ?? NULL) === GATE1_STEP05_TARGET_COUNT
      && is_array($artifacts)
      && !$agent_present,
  ];
}

function gate1_step05_system_prompt(): string {
  return <<<'PROMPT'
You draft one alt-text recommendation for one verified Drupal image-field usage.

Use only the supplied image and page context. Describe the image's meaningful content and purpose
in that context. Be concise and specific. Do not begin with "image of", "photo of", "picture of",
"graphic of", "Here is", or "Alt text:". Do not repeat the filename. Do not invent facts that are
not visible in the image or stated in the supplied page context.

Return only the structured model-output object required by
recommendation.schema.json#/$defs/model_output. The proposed_alt_text value must be nonempty and no
more than 250 Unicode characters.
PROMPT;
}

/**
 * @param array<string, mixed> $target
 * @param array<string, mixed> $context
 */
function gate1_step05_user_prompt(array $target, array $context): string {
  $existing_alt = $context['existing_alt'] === NULL ? 'null' : (string) $context['existing_alt'];
  $width = $context['image']['width'] ?? 'unknown';
  $height = $context['image']['height'] ?? 'unknown';
  return sprintf(
    "TARGET\n- Sequence: %d\n- Node UUID: %s\n- Article revision: %d\n- Field: %s\n- Delta: %d\n- File UUID: %s\n- Existing alt text: %s\n\nPAGE CONTEXT\n- Article title: %s\n- Article body: %s\n\nIMAGE CONTEXT\n- Filename: %s\n- MIME type: %s\n- Dimensions: %s x %s\n- Image input: identical PNG bytes, represented as a Base64-encoded PNG data URL with detail=auto or the Drupal AI ImageFile equivalent over the same bytes\n\nProduce the model-output object only.",
    $target['sequence'],
    $target['node_uuid'],
    $target['revision_id'],
    $target['field_name'],
    $target['delta'],
    $target['file_uuid'],
    $existing_alt,
    $context['article']['title'],
    $context['article']['body_plain'],
    $context['image']['filename'],
    $context['image']['mime_type'],
    (string) $width,
    (string) $height,
  );
}

/**
 * Creates the deterministic temporary AI Agent config.
 *
 * @return array<string, mixed>
 */
function gate1_step05_structured_output_schema(): string {
  return json_encode([
    '$schema' => 'https://json-schema.org/draft/2020-12/schema',
    'type' => 'object',
    'properties' => [
      'proposed_alt_text' => [
        'type' => 'string',
        'minLength' => 1,
        'maxLength' => 250,
      ],
    ],
    'required' => ['proposed_alt_text'],
    'additionalProperties' => FALSE,
  ], JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
}

/**
 * Builds the strict provider-level schema frozen by ADR-0006.
 */
function gate1_step05_provider_structured_output_schema(): StructuredOutputSchema {
  return new StructuredOutputSchema(
    name: 'drupal_ai_model_output',
    description: 'Raw Drupal AI model output.',
    strict: TRUE,
    json_schema: json_decode(gate1_step05_structured_output_schema(), TRUE, 512, JSON_THROW_ON_ERROR),
  );
}

/**
 * Applies and verifies the strict schema on one outgoing ChatInput.
 *
 * @return array<string, mixed>
 */
function gate1_step05_apply_provider_structured_output(ChatInput $input): array {
  $input->setChatStructuredJsonSchema(gate1_step05_provider_structured_output_schema());
  $normalized = $input->getChatStructuredJsonSchema();
  if (!is_array($normalized) || ($normalized['strict'] ?? NULL) !== TRUE) {
    throw new RuntimeException('Strict provider structured-output schema was not applied to ChatInput.');
  }
  return $normalized;
}

function gate1_step05_create_agent_config(): array {
  $storage = \Drupal::entityTypeManager()->getStorage('ai_agent');
  $existing = $storage->load(GATE1_STEP05_AGENT_ID);
  if ($existing instanceof ConfigEntityInterface) {
    $data = $existing->toArray();
    if (
      ($data['system_prompt'] ?? NULL) !== gate1_step05_system_prompt()
      || ($data['structured_output_enabled'] ?? NULL) !== TRUE
      || ($data['structured_output_schema'] ?? NULL) !== gate1_step05_structured_output_schema()
      || ($data['tools'] ?? NULL) !== []
      || ($data['tool_settings'] ?? NULL) !== []
      || ($data['tool_usage_limits'] ?? NULL) !== []
      || (int) ($data['max_loops'] ?? 0) !== 1
    ) {
      throw new RuntimeException('Existing Step 1.05 AI Agent configuration differs from the controlled design.');
    }
    return [
      'id' => $existing->id(),
      'label' => $existing->label(),
      'reused' => TRUE,
    ];
  }

  $template = $storage->load(GATE1_STEP05_TEMPLATE_AGENT_ID);
  if (!$template instanceof ConfigEntityInterface) {
    throw new RuntimeException('Pinned AI Agent template is unavailable.');
  }
  $data = $template->toArray();
  foreach ([
    'id', 'label', 'description', 'system_prompt', 'max_loops', 'default_information_tools',
    'structured_output_enabled', 'structured_output_schema', 'tools', 'tool_settings', 'tool_usage_limits',
  ] as $required_key) {
    if (!array_key_exists($required_key, $data)) {
      throw new RuntimeException('Pinned AI Agent template lacks required config key: ' . $required_key);
    }
  }

  unset($data['uuid']);
  $data['id'] = GATE1_STEP05_AGENT_ID;
  $data['label'] = 'Agentic Harness Alt Text Batch';
  $data['description'] = 'Twelve-target Gate 1 Step 1.05 execution configuration.';
  $data['system_prompt'] = gate1_step05_system_prompt();
  if (array_key_exists('secured_system_prompt', $data)) {
    $data['secured_system_prompt'] = gate1_step05_system_prompt();
  }
  if (array_key_exists('agent_instructions', $data)) {
    $data['agent_instructions'] = '';
  }
  if (array_key_exists('orchestration_agent', $data)) {
    $data['orchestration_agent'] = FALSE;
  }
  if (array_key_exists('triage_agent', $data)) {
    $data['triage_agent'] = FALSE;
  }
  $data['max_loops'] = 1;
  $data['default_information_tools'] = '';
  $data['structured_output_enabled'] = TRUE;
  $data['structured_output_schema'] = gate1_step05_structured_output_schema();
  $data['tools'] = [];
  $data['tool_settings'] = [];
  $data['tool_usage_limits'] = [];

  $entity = $storage->create($data);
  if (!$entity instanceof ConfigEntityInterface) {
    throw new RuntimeException('Drupal did not create the Step 1.05 AI Agent configuration.');
  }
  $entity->save();
  \Drupal::service('plugin.manager.ai_agents')->clearCachedDefinitions();
  return [
    'id' => $entity->id(),
    'label' => $entity->label(),
    'reused' => FALSE,
  ];
}

function gate1_step05_delete_agent_config(): void {
  $storage = \Drupal::entityTypeManager()->getStorage('ai_agent');
  $entity = $storage->load(GATE1_STEP05_AGENT_ID);
  if ($entity instanceof ConfigEntityInterface) {
    $entity->delete();
    \Drupal::service('plugin.manager.ai_agents')->clearCachedDefinitions();
  }
}

/**
 * @return array<string, mixed>
 */
function gate1_step05_safe_checkpoint(object $agent): array {
  $checkpoint = $agent->toArray();
  $encoded = gate1_step05_json($checkpoint);
  if (
    !empty($checkpoint['chat_history'])
    || preg_match('/(?:data:image|Authorization\s*:|Bearer\s+|sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9+\/]{128,}={0,2})/i', $encoded) === 1
  ) {
    throw new RuntimeException('Pre-image wrapper checkpoint contains prohibited material.');
  }
  $restored = \Drupal::service('plugin.manager.ai_agents')->createInstance(GATE1_STEP05_AGENT_ID);
  $restored->fromArray($checkpoint);
  if (
    $restored->getModelName() !== GATE1_STEP05_MODEL
    || $restored->getAiConfiguration() !== ['temperature' => GATE1_STEP05_TEMPERATURE]
  ) {
    throw new RuntimeException('Safe wrapper checkpoint could not be restored.');
  }
  return [
    'stage' => 'pre_task_pre_image_pre_provider',
    'provider_id' => $checkpoint['provider_id'] ?? GATE1_STEP05_PROVIDER,
    'model_name' => $checkpoint['model_name'] ?? GATE1_STEP05_MODEL,
    'ai_configuration' => $checkpoint['ai_configuration'] ?? ['temperature' => GATE1_STEP05_TEMPERATURE],
    'chat_history_empty' => empty($checkpoint['chat_history']),
    'files_or_images_present' => FALSE,
    'base64_or_data_url_present' => FALSE,
    'credential_or_authorization_present' => FALSE,
    'from_array_restored' => TRUE,
  ];
}

/**
 * @return array<string, mixed>
 */
function gate1_step05_model_output(string $solved, int $sequence, ?array $provider_response_metadata): array {
  $decoded = json_decode(trim($solved), TRUE);
  if (!is_array($decoded)) {
    $diagnostic = [
      'sequence' => $sequence,
      'source' => 'solve_json',
      'solve_json_type' => get_debug_type($decoded),
      'solve_json_error' => json_last_error_msg(),
      'provider_response_metadata' => $provider_response_metadata,
      'raw_output_retained' => FALSE,
    ];
    throw new RuntimeException(
      'AI Agent solve() output was not a structured JSON object; diagnostic=' . gate1_step05_json($diagnostic),
    );
  }

  $output = $decoded;
  $keys = array_keys($output);
  sort($keys);
  $required_present = array_key_exists('proposed_alt_text', $output);
  $alt = $required_present ? $output['proposed_alt_text'] : NULL;
  $trimmed_length = is_string($alt) ? mb_strlen(trim($alt)) : NULL;
  $diagnostic = [
    'sequence' => $sequence,
    'source' => 'solve_json',
    'output_type' => get_debug_type($output),
    'key_count' => count($keys),
    'exact_required_key_set' => $keys === ['proposed_alt_text'],
    'proposed_alt_text_present' => $required_present,
    'proposed_alt_text_type' => get_debug_type($alt),
    'proposed_alt_text_trimmed_length' => $trimmed_length,
    'provider_response_metadata' => $provider_response_metadata,
    'raw_output_retained' => FALSE,
  ];

  if (
    $keys !== ['proposed_alt_text']
    || !is_string($alt)
    || trim($alt) === ''
    || $trimmed_length === NULL
    || $trimmed_length > 250
  ) {
    throw new RuntimeException(
      'AI Agent solve() output does not conform to the frozen model-output schema; diagnostic=' . gate1_step05_json($diagnostic),
    );
  }
  return ['proposed_alt_text' => trim($alt)];
}

function gate1_step05_event(
  array &$artifacts,
  string $event_type,
  ?int $sequence,
  string $correlation_id,
  ?array $target,
  string $outcome,
  ?string $error_code = NULL,
): void {
  $event = [
    'schema_version' => 1,
    'event_index' => count($artifacts['events']) + 1,
    'event_type' => $event_type,
    'run_id' => $artifacts['run_id'],
    'source_framework' => 'drupal_ai',
    'occurred_at' => gate1_step05_now(),
    'sequence' => $sequence,
    'correlation_id' => $correlation_id,
    'outcome' => $outcome,
    'error_code' => $error_code,
  ];
  if ($target !== NULL) {
    $event['target'] = $target;
  }
  $artifacts['events'][] = $event;
}

/**
 * @param array<string, mixed> $artifacts
 * @param array<string, mixed>|null $target
 * @param array<string, mixed> $result
 */
function gate1_step05_trace(
  array &$artifacts,
  string $operation,
  string $correlation_id,
  ?int $sequence,
  ?array $target,
  string $started_at,
  string $completed_at,
  array $result,
  ?string $recommendation_uuid = NULL,
): void {
  $trace = [
    'operation' => $operation,
    'correlation_id' => $correlation_id,
    'started_at' => $started_at,
    'completed_at' => $completed_at,
    'ok' => TRUE,
    'sequence' => $sequence,
    'result_sha256' => 'sha256:' . gate1_step05_sha($result),
    'error' => NULL,
  ];
  if ($target !== NULL) {
    $trace['target'] = $target;
  }
  if ($recommendation_uuid !== NULL) {
    $trace['recommendation_uuid'] = $recommendation_uuid;
  }
  $artifacts['traces'][] = $trace;
}

/**
 * @param array<string, mixed> $state
 * @param array<string, mixed> $artifacts
 */
function gate1_step05_persist(array $state, array $artifacts): void {
  $collection = \Drupal::service('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);
  $collection->set(GATE1_STEP05_STATE_KEY, $state);
  $collection->set(GATE1_STEP05_ARTIFACT_KEY, $artifacts);
}

/**
 * @param array<int, array<string, mixed>> $targets
 * @return array<string, mixed>
 */
function gate1_step05_initial_state(string $run_id, array $targets): array {
  $now = gate1_step05_now();
  return [
    'schema_version' => 1,
    'run_id' => $run_id,
    'framework_origin' => 'drupal_ai',
    'status' => 'initialized',
    'target_sequence_hash' => 'sha256:' . GATE1_STEP05_TARGET_SHA256,
    'next_target_index' => 0,
    'completed_target_identities' => [],
    'recommendation_ids' => [],
    'validation_results' => [],
    'started_at' => $now,
    'updated_at' => $now,
    'completed_at' => NULL,
    'interrupted_at' => NULL,
    'resumed_at' => NULL,
    'failure_injection_armed' => TRUE,
    'failure_injection_fired' => FALSE,
    'prompt_version' => GATE1_STEP05_PROMPT_VERSION,
    'model_id' => GATE1_STEP05_MODEL,
  ];
}

/**
 * @param array<int, array<string, mixed>> $targets
 * @return array<string, mixed>
 */
function gate1_step05_initial_artifacts(string $run_id, array $targets, string $source_sha): array {
  return [
    'schema_version' => 1,
    'run_id' => $run_id,
    'targets' => $targets,
    'events' => [],
    'traces' => [],
    'model_outputs' => [],
    'recommendations' => [],
    'validation_results' => [],
    'submissions' => [],
    'statuses' => [],
    'provider_request_count_start' => 0,
    'agent_request_count_start' => 0,
    'provider_request_count_resume' => 0,
    'agent_request_count_resume' => 0,
    'automatic_retries' => 0,
    'model_callable_tool_count' => 0,
    'source_article_sha256_before' => $source_sha,
    'safe_checkpoint_verified_count' => 0,
    'raw_image_retained' => FALSE,
    'post_image_wrapper_serialization_performed' => FALSE,
  ];
}

/**
 * Retains only bounded provider-response metadata needed to classify a failed
 * structured-output request. No content, refusal text, reasoning, identifiers,
 * prompts, credentials, or raw provider payload are retained.
 *
 * @return array<string, mixed>
 */
function gate1_step05_provider_response_metadata(mixed $raw, int $sequence): array {
  $choices = is_array($raw) && isset($raw['choices']) && is_array($raw['choices'])
    ? $raw['choices']
    : [];
  $choice = isset($choices[0]) && is_array($choices[0]) ? $choices[0] : [];
  $message = isset($choice['message']) && is_array($choice['message']) ? $choice['message'] : [];

  $finish_reason_present = array_key_exists('finish_reason', $choice);
  $finish_reason_value = $finish_reason_present ? $choice['finish_reason'] : NULL;
  $finish_reason = NULL;
  if (is_string($finish_reason_value)) {
    $candidate = trim($finish_reason_value);
    if ($candidate !== '' && strlen($candidate) <= 64 && preg_match('/^[A-Za-z0-9_.-]+$/D', $candidate) === 1) {
      $finish_reason = $candidate;
    }
  }

  $content_present = array_key_exists('content', $message);
  $content = $content_present ? $message['content'] : NULL;
  $refusal_present = array_key_exists('refusal', $message);
  $refusal = $refusal_present ? $message['refusal'] : NULL;
  $tool_calls_present = array_key_exists('tool_calls', $message);
  $tool_calls = $tool_calls_present && is_array($message['tool_calls']) ? $message['tool_calls'] : [];

  return [
    'sequence' => $sequence,
    'raw_output_type' => get_debug_type($raw),
    'choice_count' => count($choices),
    'finish_reason_present' => $finish_reason_present,
    'finish_reason_type' => get_debug_type($finish_reason_value),
    'finish_reason' => $finish_reason,
    'finish_reason_safely_retained' => $finish_reason !== NULL,
    'message_content_present' => $content_present,
    'message_content_type' => get_debug_type($content),
    'message_content_non_empty' => is_string($content) ? trim($content) !== '' : ($content !== NULL),
    'message_refusal_present' => $refusal_present,
    'message_refusal_type' => get_debug_type($refusal),
    'message_refusal_non_empty' => is_string($refusal) ? trim($refusal) !== '' : ($refusal !== NULL),
    'tool_calls_present' => $tool_calls_present,
    'tool_call_count' => count($tool_calls),
    'raw_provider_output_retained' => FALSE,
    'message_content_retained' => FALSE,
    'refusal_text_retained' => FALSE,
  ];
}


/**
 * Converts an allowlisted numeric rate-limit value without retaining the
 * surrounding raw response text.
 */
function gate1_step05_rate_limit_number(mixed $value): int|float|null {
  if (is_int($value) || is_float($value)) {
    return $value;
  }
  if (!is_string($value)) {
    return NULL;
  }
  $trimmed = trim($value);
  if ($trimmed === '' || !preg_match('/^[0-9]+(?:\.[0-9]+)?$/', $trimmed)) {
    return NULL;
  }
  return str_contains($trimmed, '.') ? (float) $trimmed : (int) $trimmed;
}

/**
 * Returns a short machine-oriented scalar from an API error object.
 */
function gate1_step05_rate_limit_machine_string(mixed $value): ?string {
  if (!is_string($value)) {
    return NULL;
  }
  $trimmed = trim($value);
  if ($trimmed === '' || strlen($trimmed) > 80) {
    return NULL;
  }
  return preg_match('/^[A-Za-z0-9_.:-]+$/', $trimmed) ? $trimmed : NULL;
}

/**
 * Returns a bounded duration-like header value such as 1s, 250ms, or 6m0s.
 */
function gate1_step05_rate_limit_duration(ResponseInterface $response, string $header): ?string {
  $value = trim($response->getHeaderLine($header));
  if ($value === '' || strlen($value) > 32) {
    return NULL;
  }
  return preg_match('/^(?:[0-9]+(?:\.[0-9]+)?(?:ms|s|m|h))+$/', $value) ? $value : NULL;
}

/**
 * Extracts only allowlisted 429 classification fields from the SDK's PSR-7
 * response. Raw headers, body, request id, and human-readable error text are
 * transient only and are never returned or persisted.
 *
 * @return array<string, mixed>
 */
function gate1_step05_rate_limit_response_diagnostic(RateLimitException $exception): array {
  $response = $exception->response;
  $body_text = (string) $response->getBody();
  $decoded = json_decode($body_text, TRUE);
  $error = is_array($decoded) && is_array($decoded['error'] ?? NULL) ? $decoded['error'] : [];
  $message = is_string($error['message'] ?? NULL) ? $error['message'] : '';

  $dimension = NULL;
  $lower_message = strtolower($message);
  if (str_contains($lower_message, 'tokens per min') || str_contains($lower_message, 'tokens per minute')) {
    $dimension = 'tokens_per_minute';
  }
  elseif (str_contains($lower_message, 'requests per min') || str_contains($lower_message, 'requests per minute')) {
    $dimension = 'requests_per_minute';
  }
  elseif (str_contains($lower_message, 'requests per day')) {
    $dimension = 'requests_per_day';
  }

  $message_number = static function (string $label) use ($message): int|float|null {
    if ($message === '') {
      return NULL;
    }
    $pattern = '/\b' . preg_quote($label, '/') . ':\s*([0-9]+(?:\.[0-9]+)?)/i';
    return preg_match($pattern, $message, $matches)
      ? gate1_step05_rate_limit_number($matches[1])
      : NULL;
  };

  return [
    'http_status_code' => $response->getStatusCode(),
    'api_error_type' => gate1_step05_rate_limit_machine_string($error['type'] ?? NULL),
    'api_error_code' => gate1_step05_rate_limit_machine_string($error['code'] ?? NULL),
    'rate_limit_dimension' => $dimension,
    'rate_limit_limit' => $message_number('Limit'),
    'rate_limit_current' => $message_number('Current'),
    'rate_limit_used' => $message_number('Used'),
    'rate_limit_requested' => $message_number('Requested'),
    'x_ratelimit_limit_requests' => gate1_step05_rate_limit_number($response->getHeaderLine('x-ratelimit-limit-requests')),
    'x_ratelimit_limit_tokens' => gate1_step05_rate_limit_number($response->getHeaderLine('x-ratelimit-limit-tokens')),
    'x_ratelimit_remaining_requests' => gate1_step05_rate_limit_number($response->getHeaderLine('x-ratelimit-remaining-requests')),
    'x_ratelimit_remaining_tokens' => gate1_step05_rate_limit_number($response->getHeaderLine('x-ratelimit-remaining-tokens')),
    'x_ratelimit_reset_requests' => gate1_step05_rate_limit_duration($response, 'x-ratelimit-reset-requests'),
    'x_ratelimit_reset_tokens' => gate1_step05_rate_limit_duration($response, 'x-ratelimit-reset-tokens'),
    'retry_after_seconds' => gate1_step05_rate_limit_number($response->getHeaderLine('retry-after')),
    'raw_response_body_retained' => FALSE,
    'raw_response_headers_retained' => FALSE,
    'error_message_retained' => FALSE,
    'request_id_retained' => FALSE,
  ];
}

/**
 * Retains only bounded provider-exception classification. For the pinned
 * openai-php 429 exception, an allowlisted projection of its PSR-7 response is
 * included; raw response text and request context are not retained.
 *
 * @return array<string, mixed>
 */
function gate1_step05_provider_exception_diagnostic(AiExceptionEvent $event, int $sequence): array {
  $exception = $event->getException();
  $code = $exception->getCode();
  return [
    'sequence' => $sequence,
    'exception_class' => get_class($exception),
    'exception_code' => is_int($code) ? $code : NULL,
    'exception_code_type' => get_debug_type($code),
    'provider_exception_observed' => TRUE,
    'normal_response_event_observed' => FALSE,
    'rate_limit_response_diagnostic' => $exception instanceof RateLimitException
      ? gate1_step05_rate_limit_response_diagnostic($exception)
      : NULL,
    'exception_message_retained' => FALSE,
    'provider_input_retained' => FALSE,
    'provider_configuration_retained' => FALSE,
    'provider_debug_data_retained' => FALSE,
    'raw_provider_output_retained' => FALSE,
  ];
}

/**
 * @param array<string, int> $provider_by_sequence
 * @param array<string, int> $agent_by_sequence
 * @param array<string, array<string, mixed>> $response_metadata_by_sequence
 * @param array<string, array<string, mixed>> $provider_exception_by_sequence
 */
function gate1_step05_register_request_guards(
  array &$provider_by_sequence,
  array &$agent_by_sequence,
  array &$response_metadata_by_sequence,
  array &$provider_exception_by_sequence,
  ?int &$current_sequence,
): void {
  $dispatcher = \Drupal::service('event_dispatcher');
  $dispatcher->addListener(
    PreGenerateResponseEvent::EVENT_NAME,
    static function (PreGenerateResponseEvent $event) use (&$provider_by_sequence, &$current_sequence): void {
      if ($current_sequence === NULL) {
        throw new RuntimeException('Provider request occurred outside an active target.');
      }
      $input = $event->getInput();
      if (!$input instanceof ChatInput) {
        throw new RuntimeException('Step 1.05 provider boundary did not expose ChatInput.');
      }
      gate1_step05_apply_provider_structured_output($input);
      $key = (string) $current_sequence;
      $provider_by_sequence[$key] = ($provider_by_sequence[$key] ?? 0) + 1;
      if ($provider_by_sequence[$key] > 1) {
        throw new RuntimeException('Second provider request blocked for target sequence ' . $current_sequence . '.');
      }
    },
    10000,
  );
  $dispatcher->addListener(
    AgentRequestEvent::EVENT_NAME,
    static function () use (&$agent_by_sequence, &$current_sequence): void {
      if ($current_sequence === NULL) {
        throw new RuntimeException('AI Agent request occurred outside an active target.');
      }
      $key = (string) $current_sequence;
      $agent_by_sequence[$key] = ($agent_by_sequence[$key] ?? 0) + 1;
      if ($agent_by_sequence[$key] > 1) {
        throw new RuntimeException('Second AI Agent request blocked for target sequence ' . $current_sequence . '.');
      }
    },
    10000,
  );
  $dispatcher->addListener(
    AgentResponseEvent::EVENT_NAME,
    static function (AgentResponseEvent $event) use (&$response_metadata_by_sequence, &$current_sequence): void {
      if ($current_sequence === NULL) {
        throw new RuntimeException('AI Agent response occurred outside an active target.');
      }
      $response_metadata_by_sequence[(string) $current_sequence] = gate1_step05_provider_response_metadata(
        $event->getResponse()->getRawOutput(),
        $current_sequence,
      );
    },
    10000,
  );
  $dispatcher->addListener(
    AiExceptionEvent::class,
    static function (AiExceptionEvent $event) use (&$provider_exception_by_sequence, &$current_sequence): void {
      if ($current_sequence === NULL) {
        throw new RuntimeException('AI provider exception occurred outside an active target.');
      }
      $provider_exception_by_sequence[(string) $current_sequence] = gate1_step05_provider_exception_diagnostic(
        $event,
        $current_sequence,
      );
    },
    10000,
  );
}

/**
 * Isolates each moderation request into its own conservative minute window.
 *
 * The pinned OpenAI provider performs moderation before the chat request. The
 * Tier-1 moderation path was observed to return an opaque HTTP 429 at sequence
 * 3 while the chat model itself remained far below its separate limits. A
 * 65-second deterministic wait before sequences 2-12 preserves moderation and
 * zero-retry semantics while preventing multiple target moderation requests
 * from accumulating inside the same nominal 60-second TPM window.
 */
function gate1_step05_apply_moderation_pacing(int $sequence): void {
  if ($sequence <= 1) {
    return;
  }
  $remaining = sleep(GATE1_STEP05_MODERATION_PACING_SECONDS);
  if ($remaining !== 0) {
    throw new RuntimeException('Moderation rate-window pacing wait was interrupted.');
  }
}

/**
 * Processes one target and persists the completed target before returning.
 *
 * @param array<string, mixed> $state
 * @param array<string, mixed> $artifacts
 * @param array<string, mixed> $target
 * @param array<string, int> $provider_by_sequence
 * @param array<string, int> $agent_by_sequence
 * @param array<string, array<string, mixed>> $response_metadata_by_sequence
 * @param array<string, array<string, mixed>> $provider_exception_by_sequence
 */
function gate1_step05_process_target(
  array &$state,
  array &$artifacts,
  array $target,
  array &$provider_by_sequence,
  array &$agent_by_sequence,
  array &$response_metadata_by_sequence,
  array &$provider_exception_by_sequence,
  ?int &$current_sequence,
): void {
  $container = \Drupal::getContainer();
  $sequence = (int) $target['sequence'];
  $correlation = sprintf('%s:s%02d', $state['run_id'], $sequence);
  gate1_step05_event($artifacts, 'target_started', $sequence, $correlation, $target, 'started');

  $context_started = gate1_step05_now();
  $context_output = gate1_step05_adapter('get_image_context', 'target', $target);
  $context_completed = gate1_step05_now();
  $context = $context_output['data'];
  gate1_step05_trace(
    $artifacts,
    'get_image_context',
    $correlation . ':context',
    $sequence,
    $target,
    $context_started,
    $context_completed,
    $context,
  );
  gate1_step05_event($artifacts, 'context_collected', $sequence, $correlation, $target, 'passed');

  if (($context['target'] ?? NULL) !== $target) {
    throw new RuntimeException('Authorized image context target identity differs at sequence ' . $sequence . '.');
  }
  $file = gate1_step05_file_resolver()->resolve($context);
  if (!$file instanceof FileInterface || $file->uuid() !== $target['file_uuid']) {
    throw new RuntimeException('File resolver identity differs at sequence ' . $sequence . '.');
  }

  gate1_step05_apply_moderation_pacing($sequence);

  $agent = $container->get('plugin.manager.ai_agents')->createInstance(GATE1_STEP05_AGENT_ID);
  foreach (['setAiProvider', 'setModelName', 'setAiConfiguration', 'overrideFunctions', 'getFunctions', 'toArray', 'fromArray', 'setTask', 'determineSolvability', 'solve'] as $method) {
    if (!method_exists($agent, $method)) {
      throw new RuntimeException('Pinned AI Agent wrapper lacks required method: ' . $method);
    }
  }
  $provider = $container->get('ai.provider')->createInstance(GATE1_STEP05_PROVIDER);
  $provider->setConfiguration(['temperature' => GATE1_STEP05_TEMPERATURE]);
  $agent->setAiProvider($provider);
  $agent->setModelName(GATE1_STEP05_MODEL);
  $agent->setAiConfiguration(['temperature' => GATE1_STEP05_TEMPERATURE]);
  $agent->overrideFunctions(['tools' => [], 'tool_usage_limits' => [], 'tool_settings' => []]);
  $functions = $agent->getFunctions();
  if (!empty($functions['normalized']) || !empty($functions['executable'])) {
    throw new RuntimeException('Batch AI Agent unexpectedly exposes model-callable tools.');
  }
  gate1_step05_safe_checkpoint($agent);
  $artifacts['safe_checkpoint_verified_count']++;

  $task = new Task(gate1_step05_user_prompt($target, $context));
  $task->setFiles([$file]);
  $agent->setTask($task);
  $current_sequence = $sequence;
  gate1_step05_event($artifacts, 'model_invocation_started', $sequence, $correlation, $target, 'started');
  $agent->determineSolvability();
  $solved = (string) $agent->solve();
  $current_sequence = NULL;

  if (($provider_by_sequence[(string) $sequence] ?? 0) !== 1) {
    throw new RuntimeException('Target did not make exactly one provider request at sequence ' . $sequence . '.');
  }
  if (($agent_by_sequence[(string) $sequence] ?? 0) !== 1) {
    throw new RuntimeException('Target did not make exactly one AI Agent request at sequence ' . $sequence . '.');
  }
  $provider_response_metadata = $response_metadata_by_sequence[(string) $sequence] ?? NULL;
  if (!is_array($provider_response_metadata) || ($provider_response_metadata['sequence'] ?? NULL) !== $sequence) {
    $provider_exception_diagnostic = $provider_exception_by_sequence[(string) $sequence] ?? NULL;
    if (
      is_array($provider_exception_diagnostic)
      && ($provider_exception_diagnostic['sequence'] ?? NULL) === $sequence
    ) {
      throw new RuntimeException(
        'AI provider exception observed before a normal response at sequence ' . $sequence
        . '; provider_exception_diagnostic=' . gate1_step05_json($provider_exception_diagnostic),
      );
    }
    throw new RuntimeException('Sanitized provider response metadata was not captured at sequence ' . $sequence . '.');
  }

  $model_output = gate1_step05_model_output($solved, $sequence, $provider_response_metadata);
  unset($response_metadata_by_sequence[(string) $sequence], $provider_exception_by_sequence[(string) $sequence]);
  $artifacts['model_outputs'][] = [
    'sequence' => $sequence,
    'target' => $target,
    'model_output' => $model_output,
  ];
  gate1_step05_event($artifacts, 'model_output_received', $sequence, $correlation, $target, 'passed');

  $evidence_payload = [
    'schema_version' => 1,
    'target' => $target,
    'context_evidence_hash' => $context['evidence_hash'],
    'article_title_sha256' => gate1_step05_sha($context['article']['title']),
    'article_body_sha256' => gate1_step05_sha($context['article']['body_plain']),
    'image' => [
      'file_uuid' => $context['image']['file_uuid'],
      'filename' => $context['image']['filename'],
      'mime_type' => $context['image']['mime_type'],
      'width' => $context['image']['width'] ?? NULL,
      'height' => $context['image']['height'] ?? NULL,
      'byte_length' => $context['image']['byte_length'],
      'sha256' => $context['image']['sha256'],
      'representation_kind' => $context['image']['representation']['kind'] ?? NULL,
      'representation_value_retained' => FALSE,
    ],
    'model_output' => $model_output,
    'provider' => GATE1_STEP05_PROVIDER,
    'model' => GATE1_STEP05_MODEL,
    'temperature' => GATE1_STEP05_TEMPERATURE,
    'provider_request_count_for_target' => 1,
  ];
  $recommendation = [
    'schema_version' => 1,
    'target' => $target,
    'proposed_alt_text' => $model_output['proposed_alt_text'],
    'source_framework' => 'drupal_ai',
    'run_id' => $state['run_id'],
    'evidence_hash' => 'sha256:' . gate1_step05_sha($evidence_payload),
    'validator_version' => GATE1_STEP05_VALIDATOR_VERSION,
  ];

  $validated = $container->get('agentic_harness_tools.recommendation_validator')->validate($recommendation);
  $recommendation = $validated['recommendation'];
  $validation = [
    'sequence' => $sequence,
    'target' => $target,
    'structured_output_schema_valid' => TRUE,
    'deterministic_validation_passed' => TRUE,
    'errors' => [],
  ];
  $artifacts['recommendations'][] = [
    'sequence' => $sequence,
    'target' => $target,
    'recommendation' => $recommendation,
  ];
  $artifacts['validation_results'][] = $validation;
  gate1_step05_event($artifacts, 'validation_completed', $sequence, $correlation, $target, 'passed');

  $submit_started = gate1_step05_now();
  $submission = gate1_step05_adapter('submit_recommendation', 'recommendation', $recommendation)['data'];
  $submit_completed = gate1_step05_now();
  gate1_step05_trace(
    $artifacts,
    'submit_recommendation',
    $correlation . ':submit',
    $sequence,
    $target,
    $submit_started,
    $submit_completed,
    $submission,
    (string) $submission['uuid'],
  );

  $replay_started = gate1_step05_now();
  $replay = gate1_step05_adapter('submit_recommendation', 'recommendation', $recommendation)['data'];
  $replay_completed = gate1_step05_now();
  gate1_step05_trace(
    $artifacts,
    'submit_recommendation',
    $correlation . ':replay',
    $sequence,
    $target,
    $replay_started,
    $replay_completed,
    $replay,
    (string) $replay['uuid'],
  );
  foreach (['node_id', 'uuid', 'revision_id'] as $identity_key) {
    if (($submission[$identity_key] ?? NULL) !== ($replay[$identity_key] ?? NULL)) {
      throw new RuntimeException('Submission idempotent replay identity changed at sequence ' . $sequence . '.');
    }
  }

  $status_started = gate1_step05_now();
  $pending = gate1_step05_adapter(
    'get_recommendation_status',
    'recommendation_id',
    (string) $submission['uuid'],
  )['data'];
  $status_completed = gate1_step05_now();
  gate1_step05_trace(
    $artifacts,
    'get_recommendation_status',
    $correlation . ':status',
    $sequence,
    $target,
    $status_started,
    $status_completed,
    $pending,
    (string) $submission['uuid'],
  );
  if (($pending['status'] ?? NULL) !== 'pending') {
    throw new RuntimeException('Submitted recommendation did not enter pending status at sequence ' . $sequence . '.');
  }

  $submission_evidence = [
    'sequence' => $sequence,
    'target' => $target,
    'node_id' => $submission['node_id'],
    'uuid' => $submission['uuid'],
    'revision_id' => $submission['revision_id'],
    'initial_status' => 'pending',
    'idempotent_replay_same_identity' => TRUE,
  ];
  $artifacts['submissions'][] = $submission_evidence;
  $artifacts['statuses'][] = [
    'recommendation_uuid' => $pending['uuid'],
    'revision_id' => $pending['revision_id'],
    'status' => 'pending',
    'observed_at' => gate1_step05_now(),
  ];
  gate1_step05_event($artifacts, 'recommendation_submitted', $sequence, $correlation, $target, 'persisted');
  gate1_step05_event($artifacts, 'status_observed', $sequence, $correlation, $target, 'passed');

  if (gate1_step05_snapshot()['article_source_sha256'] !== GATE1_STEP05_SOURCE_SHA256) {
    throw new RuntimeException('Source Article projection changed at sequence ' . $sequence . '.');
  }

  $state['completed_target_identities'][] = $target;
  $state['recommendation_ids'][] = [
    'sequence' => $sequence,
    'node_id' => $submission['node_id'],
    'uuid' => $submission['uuid'],
    'revision_id' => $submission['revision_id'],
  ];
  $state['validation_results'][] = $validation;
  $state['next_target_index'] = $sequence;
  $state['updated_at'] = gate1_step05_now();
  gate1_step05_event($artifacts, 'target_completed', $sequence, $correlation, $target, 'persisted');
  gate1_step05_persist($state, $artifacts);
}

function gate1_step05_expect_resolver_failure(array $context): void {
  try {
    gate1_step05_file_resolver()->resolve($context);
  }
  catch (RuntimeException) {
    return;
  }
  throw new RuntimeException('A declared File resolver negative control unexpectedly passed.');
}

/**
 * Model-free, reset-bounded runtime compatibility proof.
 *
 * @return array<string, mixed>
 */
function gate1_step05_preflight(): array {
  $container = \Drupal::getContainer();
  $snapshot = gate1_step05_snapshot();
  if (!$snapshot['seeded_clean']) {
    throw new RuntimeException('Step 1.05 preflight requires seeded-clean state.');
  }

  $provider_requests = 0;
  $agent_requests = 0;
  $container->get('event_dispatcher')->addListener(
    PreGenerateResponseEvent::EVENT_NAME,
    static function () use (&$provider_requests): void {
      $provider_requests++;
      throw new RuntimeException('Provider request prohibited during Step 1.05 preflight.');
    },
    10000,
  );
  $container->get('event_dispatcher')->addListener(
    AgentRequestEvent::EVENT_NAME,
    static function () use (&$agent_requests): void {
      $agent_requests++;
      throw new RuntimeException('AI Agent request prohibited during Step 1.05 preflight.');
    },
    10000,
  );

  $current_user = $container->get('current_user');
  $original = $current_user->getAccount();
  $created = FALSE;
  try {
    $current_user->setAccount(gate1_step05_user('agent_bot'));
    $targets = gate1_step05_discover_targets();
    $verified = 0;
    $canonical_context = NULL;
    foreach ($targets as $target) {
      $context = gate1_step05_adapter('get_image_context', 'target', $target)['data'];
      if (($context['target'] ?? NULL) !== $target) {
        throw new RuntimeException('Preflight context target identity differs.');
      }
      $file = gate1_step05_file_resolver()->resolve($context);
      if (!$file instanceof FileInterface || $file->uuid() !== $target['file_uuid']) {
        throw new RuntimeException('Preflight File resolver identity differs.');
      }
      $verified++;
      if (($target['sequence'] ?? NULL) === 1) {
        $canonical_context = $context;
      }
    }
    if (!is_array($canonical_context)) {
      throw new RuntimeException('Canonical context was not collected.');
    }

    $negative_count = 0;
    foreach (['filename', 'mime_type', 'byte_length', 'sha256'] as $field) {
      $bad = $canonical_context;
      $bad['image'][$field] = match ($field) {
        'filename' => 'mismatch-' . $bad['image'][$field],
        'mime_type' => 'image/x-mismatch',
        'byte_length' => $bad['image'][$field] + 1,
        'sha256' => str_repeat('0', 64),
      };
      gate1_step05_expect_resolver_failure($bad);
      $negative_count++;
    }
    $bad = $canonical_context;
    $bad['image']['file_uuid'] = '00000000-0000-4000-8000-000000000000';
    gate1_step05_expect_resolver_failure($bad);
    $negative_count++;
    $bad = $canonical_context;
    $bad['image']['uri'] = 'https://example.invalid/image.png';
    gate1_step05_expect_resolver_failure($bad);
    $negative_count++;

    gate1_step05_create_agent_config();
    $created = TRUE;
    $agent = $container->get('plugin.manager.ai_agents')->createInstance(GATE1_STEP05_AGENT_ID);
    $provider = $container->get('ai.provider')->createInstance(GATE1_STEP05_PROVIDER);
    $provider->setConfiguration(['temperature' => GATE1_STEP05_TEMPERATURE]);
    $agent->setAiProvider($provider);
    $agent->setModelName(GATE1_STEP05_MODEL);
    $agent->setAiConfiguration(['temperature' => GATE1_STEP05_TEMPERATURE]);
    $agent->overrideFunctions(['tools' => [], 'tool_usage_limits' => [], 'tool_settings' => []]);
    $functions = $agent->getFunctions();
    if (!empty($functions['normalized']) || !empty($functions['executable'])) {
      throw new RuntimeException('Preflight AI Agent exposes model-callable tools.');
    }
    $checkpoint = gate1_step05_safe_checkpoint($agent);

    $schema_probe = new ChatInput([]);
    $normalized_schema = gate1_step05_apply_provider_structured_output($schema_probe);
    $response_metadata_capture_verified = method_exists(AgentResponseEvent::class, 'getResponse')
      && method_exists(\Drupal\ai\OperationType\Chat\ChatOutput::class, 'getRawOutput');
    if (!$response_metadata_capture_verified) {
      throw new RuntimeException('Pinned AI Agents response event does not expose ChatOutput::getRawOutput().');
    }

    $provider_proxy_path = dirname(DRUPAL_ROOT) . '/web/modules/contrib/ai/src/Plugin/ProviderProxy.php';
    $provider_proxy_source = is_file($provider_proxy_path)
      ? (string) file_get_contents($provider_proxy_path)
      : '';
    $provider_exception_capture_verified = class_exists(AiExceptionEvent::class)
      && method_exists(AiExceptionEvent::class, 'getException')
      && str_contains($provider_proxy_source, 'new AiExceptionEvent(')
      && str_contains($provider_proxy_source, '$this->eventDispatcher->dispatch($event);');
    if (!$provider_exception_capture_verified) {
      throw new RuntimeException('Pinned Drupal AI provider-exception event surface is unavailable.');
    }

    $rate_limit_exception_path = dirname(DRUPAL_ROOT) . '/vendor/openai-php/client/src/Exceptions/RateLimitException.php';
    $http_transporter_path = dirname(DRUPAL_ROOT) . '/vendor/openai-php/client/src/Transporters/HttpTransporter.php';
    $rate_limit_exception_source = is_file($rate_limit_exception_path)
      ? (string) file_get_contents($rate_limit_exception_path)
      : '';
    $http_transporter_source = is_file($http_transporter_path)
      ? (string) file_get_contents($http_transporter_path)
      : '';
    $rate_limit_response_property = class_exists(RateLimitException::class)
      && property_exists(RateLimitException::class, 'response')
      ? new ReflectionProperty(RateLimitException::class, 'response')
      : NULL;
    $rate_limit_response_diagnostics_verified = $rate_limit_response_property instanceof ReflectionProperty
      && $rate_limit_response_property->isPublic()
      && hash('sha256', $rate_limit_exception_source) === 'f7f3f5948563ae789737ff84cfaef2eb57a98afa2ffa491f0cfc4d83fcbcd2ad'
      && str_contains($rate_limit_exception_source, 'public ResponseInterface $response')
      && str_contains($http_transporter_source, '$response->getStatusCode() !== 429')
      && str_contains($http_transporter_source, 'throw new RateLimitException($response);');
    if (!$rate_limit_response_diagnostics_verified) {
      throw new RuntimeException('Pinned openai-php 429 response surface is unavailable.');
    }

    $openai_settings = $container->get('config.factory')->get('ai_provider_openai.settings');
    $key_reference = (string) $openai_settings->get('api_key');
    if ($key_reference === '') {
      throw new RuntimeException('OpenAI provider key reference is not configured.');
    }
    $moderation_enabled = $openai_settings->get('moderation') === TRUE;
    if (!$moderation_enabled) {
      throw new RuntimeException('Step 1.05 requires the pinned OpenAI moderation pre-check to remain enabled.');
    }

    return [
      'schema_version' => 1,
      'status' => 'pass',
      'snapshot' => $snapshot,
      'target_count' => count($targets),
      'target_sequence_sha256' => GATE1_STEP05_TARGET_SHA256,
      'file_identity_verified_count' => $verified,
      'file_negative_controls_rejected' => $negative_count,
      'safe_wrapper_checkpoint' => $checkpoint,
      'failure_after_sequence' => GATE1_STEP05_FAILURE_AFTER_SEQUENCE,
      'resume_at_sequence' => GATE1_STEP05_RESUME_SEQUENCE,
      'model_callable_tool_count' => 0,
      'strict_provider_schema_preflight_verified' => ($normalized_schema['strict'] ?? NULL) === TRUE,
      'raw_model_output_method' => 'solve',
      'agent_structured_output_used_as_raw_model_output' => FALSE,
      'response_metadata_capture_preflight_verified' => TRUE,
      'response_event' => AgentResponseEvent::EVENT_NAME,
      'response_raw_output_accessor' => 'getRawOutput',
      'provider_response_content_retained' => FALSE,
      'provider_refusal_text_retained' => FALSE,
      'provider_exception_capture_preflight_verified' => TRUE,
      'provider_exception_event' => AiExceptionEvent::class,
      'provider_exception_accessor' => 'getException',
      'provider_exception_message_retained' => FALSE,
      'provider_exception_input_retained' => FALSE,
      'rate_limit_response_diagnostics_preflight_verified' => TRUE,
      'rate_limit_exception_class' => RateLimitException::class,
      'rate_limit_response_property' => 'response',
      'rate_limit_http_status_code' => 429,
      'rate_limit_response_body_retained' => FALSE,
      'rate_limit_response_headers_retained' => FALSE,
      'rate_limit_error_message_retained' => FALSE,
      'rate_limit_request_id_retained' => FALSE,
      'moderation_rate_pacing_preflight_verified' => TRUE,
      'moderation_rate_pacing_seconds' => GATE1_STEP05_MODERATION_PACING_SECONDS,
      'openai_moderation_enabled' => TRUE,
      'configured_key_reference_present' => TRUE,
      'configured_key_value_retained' => FALSE,
      'provider_request_count' => $provider_requests,
      'agent_request_count' => $agent_requests,
      'model_call_performed' => FALSE,
      'network_call_performed' => FALSE,
      'raw_image_retained' => FALSE,
      'post_image_wrapper_serialization_performed' => FALSE,
    ];
  }
  finally {
    if ($created) {
      gate1_step05_delete_agent_config();
    }
    $current_user->setAccount($original);
  }
}

/**
 * Processes sequences 1-6 and deliberately interrupts after sequence 6 has
 * been fully persisted and before sequence 7 begins.
 *
 * @return array<string, mixed>
 */
function gate1_step05_start(string $run_id): array {
  if (preg_match('/^drupal_ai-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$/', $run_id) !== 1) {
    throw new RuntimeException('Run ID does not conform to the frozen Drupal AI pattern.');
  }

  $container = \Drupal::getContainer();
  $lock = $container->get('lock.persistent');
  if (!$lock->acquire(GATE1_STEP05_LOCK, 1800.0)) {
    throw new RuntimeException('Batch run lock is unavailable.');
  }
  $current_user = $container->get('current_user');
  $original = $current_user->getAccount();
  $collection = $container->get('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);

  try {
    if ($collection->get(GATE1_STEP05_STATE_KEY) !== NULL || $collection->get(GATE1_STEP05_ARTIFACT_KEY) !== NULL) {
      throw new RuntimeException('Step 1.05 batch runtime state already exists.');
    }
    $before = gate1_step05_snapshot();
    if (!$before['seeded_clean']) {
      throw new RuntimeException('Step 1.05 start requires seeded-clean state.');
    }

    $current_user->setAccount(gate1_step05_user('agent_bot'));
    $discovery_started = gate1_step05_now();
    $targets = gate1_step05_discover_targets();
    $discovery_completed = gate1_step05_now();
    $state = gate1_step05_initial_state($run_id, $targets);
    $artifacts = gate1_step05_initial_artifacts($run_id, $targets, $before['article_source_sha256']);
    gate1_step05_trace(
      $artifacts,
      'find_images_needing_review',
      $run_id . ':discover',
      NULL,
      NULL,
      $discovery_started,
      $discovery_completed,
      ['targets' => $targets, 'total_count' => count($targets)],
    );
    gate1_step05_event($artifacts, 'run_initialized', NULL, $run_id . ':run', NULL, 'persisted');
    $state['status'] = 'running';
    $state['updated_at'] = gate1_step05_now();
    gate1_step05_event($artifacts, 'run_started', NULL, $run_id . ':run', NULL, 'started');
    gate1_step05_persist($state, $artifacts);

    gate1_step05_create_agent_config();
    $provider_by_sequence = [];
    $agent_by_sequence = [];
    $response_metadata_by_sequence = [];
    $provider_exception_by_sequence = [];
    $current_sequence = NULL;
    gate1_step05_register_request_guards(
      $provider_by_sequence,
      $agent_by_sequence,
      $response_metadata_by_sequence,
      $provider_exception_by_sequence,
      $current_sequence,
    );

    for ($index = 0; $index < GATE1_STEP05_FAILURE_AFTER_SEQUENCE; $index++) {
      gate1_step05_process_target(
        $state,
        $artifacts,
        $targets[$index],
        $provider_by_sequence,
        $agent_by_sequence,
        $response_metadata_by_sequence,
        $provider_exception_by_sequence,
        $current_sequence,
      );
    }

    $state['status'] = 'interrupted';
    $state['failure_injection_fired'] = TRUE;
    $state['interrupted_at'] = gate1_step05_now();
    $state['updated_at'] = $state['interrupted_at'];
    gate1_step05_event(
      $artifacts,
      'failure_injected',
      GATE1_STEP05_FAILURE_AFTER_SEQUENCE,
      $run_id . ':failure-seam',
      $targets[GATE1_STEP05_FAILURE_AFTER_SEQUENCE - 1],
      'interrupted',
      'GATE1_STEP05_DETERMINISTIC_MIDPOINT',
    );
    $artifacts['provider_request_count_start'] = array_sum($provider_by_sequence);
    $artifacts['agent_request_count_start'] = array_sum($agent_by_sequence);
    gate1_step05_persist($state, $artifacts);

    if ($artifacts['provider_request_count_start'] !== GATE1_STEP05_FAILURE_AFTER_SEQUENCE) {
      throw new RuntimeException('Start phase provider request count differs from six.');
    }
    if ($artifacts['agent_request_count_start'] !== GATE1_STEP05_FAILURE_AFTER_SEQUENCE) {
      throw new RuntimeException('Start phase AI Agent request count differs from six.');
    }

    return [
      'schema_version' => 1,
      'status' => 'interrupted',
      'run_id' => $run_id,
      'failure_injection_fired' => TRUE,
      'failure_after_sequence' => 6,
      'failure_before_sequence' => 7,
      'resume_at_sequence' => 7,
      'completed_sequences' => [1, 2, 3, 4, 5, 6],
      'next_target_index' => $state['next_target_index'],
      'provider_request_count' => $artifacts['provider_request_count_start'],
      'agent_request_count' => $artifacts['agent_request_count_start'],
      'automatic_retries' => 0,
      'recommendation_count' => count($artifacts['submissions']),
      'pending_status_count' => count($artifacts['statuses']),
      'state' => $state,
      'raw_image_retained' => FALSE,
      'post_image_wrapper_serialization_performed' => FALSE,
      'human_review_started' => FALSE,
      'step_1_06_started' => FALSE,
    ];
  }
  catch (Throwable $exception) {
    $state = $collection->get(GATE1_STEP05_STATE_KEY);
    if (is_array($state) && ($state['status'] ?? NULL) !== 'interrupted') {
      $state['status'] = 'failed';
      $state['updated_at'] = gate1_step05_now();
      $collection->set(GATE1_STEP05_STATE_KEY, $state);
    }
    throw $exception;
  }
  finally {
    $current_user->setAccount($original);
    $lock->release(GATE1_STEP05_LOCK);
  }
}

/**
 * Resumes the same run at sequence 7 and completes through sequence 12.
 *
 * @return array<string, mixed>
 */
function gate1_step05_resume(): array {
  $container = \Drupal::getContainer();
  $lock = $container->get('lock.persistent');
  if (!$lock->acquire(GATE1_STEP05_LOCK, 1800.0)) {
    throw new RuntimeException('Batch run lock is unavailable.');
  }
  $current_user = $container->get('current_user');
  $original = $current_user->getAccount();
  $collection = $container->get('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);

  try {
    $state = $collection->get(GATE1_STEP05_STATE_KEY);
    $artifacts = $collection->get(GATE1_STEP05_ARTIFACT_KEY);
    if (!is_array($state) || !is_array($artifacts)) {
      throw new RuntimeException('Interrupted Step 1.05 batch state is unavailable.');
    }
    if (($state['status'] ?? NULL) !== 'interrupted') {
      throw new RuntimeException('Step 1.05 run is not at the deterministic interruption boundary.');
    }
    if (($state['next_target_index'] ?? NULL) !== GATE1_STEP05_FAILURE_AFTER_SEQUENCE) {
      throw new RuntimeException('Step 1.05 resume index is not six.');
    }
    if (($state['failure_injection_armed'] ?? NULL) !== TRUE || ($state['failure_injection_fired'] ?? NULL) !== TRUE) {
      throw new RuntimeException('Step 1.05 failure seam state is invalid.');
    }
    if (count($state['completed_target_identities'] ?? []) !== 6 || count($state['recommendation_ids'] ?? []) !== 6) {
      throw new RuntimeException('Step 1.05 persisted first-half cardinality differs from six.');
    }

    $current_user->setAccount(gate1_step05_user('agent_bot'));
    $targets = gate1_step05_discover_targets();
    if (($artifacts['targets'] ?? NULL) !== $targets) {
      throw new RuntimeException('Frozen target sequence changed between start and resume.');
    }
    $source_at_resume = gate1_step05_snapshot()['article_source_sha256'];
    if ($source_at_resume !== GATE1_STEP05_SOURCE_SHA256) {
      throw new RuntimeException('Source Article projection changed before resume.');
    }

    gate1_step05_create_agent_config();
    $state['status'] = 'resuming';
    $state['resumed_at'] = gate1_step05_now();
    $state['updated_at'] = $state['resumed_at'];
    gate1_step05_event($artifacts, 'run_resumed', GATE1_STEP05_RESUME_SEQUENCE, $state['run_id'] . ':resume', $targets[6], 'resumed');
    gate1_step05_persist($state, $artifacts);

    $provider_by_sequence = [];
    $agent_by_sequence = [];
    $response_metadata_by_sequence = [];
    $provider_exception_by_sequence = [];
    $current_sequence = NULL;
    gate1_step05_register_request_guards(
      $provider_by_sequence,
      $agent_by_sequence,
      $response_metadata_by_sequence,
      $provider_exception_by_sequence,
      $current_sequence,
    );

    for ($index = GATE1_STEP05_FAILURE_AFTER_SEQUENCE; $index < GATE1_STEP05_TARGET_COUNT; $index++) {
      gate1_step05_process_target(
        $state,
        $artifacts,
        $targets[$index],
        $provider_by_sequence,
        $agent_by_sequence,
        $response_metadata_by_sequence,
        $provider_exception_by_sequence,
        $current_sequence,
      );
    }

    $artifacts['provider_request_count_resume'] = array_sum($provider_by_sequence);
    $artifacts['agent_request_count_resume'] = array_sum($agent_by_sequence);
    if ($artifacts['provider_request_count_resume'] !== 6 || $artifacts['agent_request_count_resume'] !== 6) {
      throw new RuntimeException('Resume phase did not make exactly six agent/provider requests.');
    }
    if (count($artifacts['submissions']) !== 12 || count($artifacts['statuses']) !== 12) {
      throw new RuntimeException('Completed batch does not contain twelve submissions and statuses.');
    }
    $uuids = array_column($artifacts['submissions'], 'uuid');
    if (count(array_unique($uuids)) !== 12) {
      throw new RuntimeException('Completed batch contains duplicate recommendation UUIDs.');
    }

    $state['status'] = 'completed';
    $state['completed_at'] = gate1_step05_now();
    $state['updated_at'] = $state['completed_at'];
    gate1_step05_event($artifacts, 'run_completed', NULL, $state['run_id'] . ':run', NULL, 'completed');
    $artifacts['source_article_sha256_after'] = gate1_step05_snapshot()['article_source_sha256'];
    if ($artifacts['source_article_sha256_after'] !== GATE1_STEP05_SOURCE_SHA256) {
      throw new RuntimeException('Source Article projection changed during the batch.');
    }
    gate1_step05_persist($state, $artifacts);
    gate1_step05_delete_agent_config();

    return [
      'schema_version' => 1,
      'status' => 'completed',
      'run_id' => $state['run_id'],
      'resumed_at_sequence' => 7,
      'completed_sequences_after_resume' => [7, 8, 9, 10, 11, 12],
      'provider_request_count' => $artifacts['provider_request_count_resume'],
      'agent_request_count' => $artifacts['agent_request_count_resume'],
      'model_call_count_total' => $artifacts['provider_request_count_start'] + $artifacts['provider_request_count_resume'],
      'automatic_retries' => 0,
      'duplicate_count' => 0,
      'recommendation_count' => count($artifacts['submissions']),
      'pending_status_count' => count($artifacts['statuses']),
      'source_article_unchanged' => TRUE,
      'human_review_completed' => FALSE,
      'state' => $state,
      'raw_image_retained' => FALSE,
      'post_image_wrapper_serialization_performed' => FALSE,
      'step_1_06_started' => FALSE,
    ];
  }
  finally {
    $current_user->setAccount($original);
    $lock->release(GATE1_STEP05_LOCK);
  }
}

/**
 * @return array<string, mixed>
 */
function gate1_step05_status(): array {
  $collection = \Drupal::service('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);
  $state = $collection->get(GATE1_STEP05_STATE_KEY);
  $artifacts = $collection->get(GATE1_STEP05_ARTIFACT_KEY);
  if (!is_array($state)) {
    return [
      'schema_version' => 1,
      'status' => 'not_started',
      'provider_request_count' => 0,
    ];
  }
  return [
    'schema_version' => 1,
    'status' => (string) ($state['status'] ?? 'unknown'),
    'run_id' => $state['run_id'] ?? NULL,
    'next_target_index' => $state['next_target_index'] ?? NULL,
    'completed_target_count' => count($state['completed_target_identities'] ?? []),
    'recommendation_count' => is_array($artifacts) ? count($artifacts['submissions'] ?? []) : 0,
    'pending_status_count' => is_array($artifacts) ? count($artifacts['statuses'] ?? []) : 0,
    'failure_injection_fired' => $state['failure_injection_fired'] ?? FALSE,
    'provider_request_count' => 0,
  ];
}

/**
 * Sanitized state/artifact export used by the shell runner to write evidence.
 *
 * @return array<string, mixed>
 */
function gate1_step05_export(): array {
  $collection = \Drupal::service('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);
  $state = $collection->get(GATE1_STEP05_STATE_KEY);
  $artifacts = $collection->get(GATE1_STEP05_ARTIFACT_KEY);
  if (!is_array($state) || !is_array($artifacts)) {
    throw new RuntimeException('Step 1.05 runtime state/artifacts are unavailable.');
  }
  $encoded = gate1_step05_json(['state' => $state, 'artifacts' => $artifacts]);
  if (preg_match('/(?:data:image\/[^;]+;base64,|Authorization\s*:|Bearer\s+|sk-[A-Za-z0-9_-]{20,})/i', $encoded) === 1) {
    throw new RuntimeException('Step 1.05 export contains prohibited retained material.');
  }
  return [
    'schema_version' => 1,
    'state' => $state,
    'artifacts' => $artifacts,
    'snapshot' => gate1_step05_snapshot(),
  ];
}

function gate1_step05_clear_state(): array {
  $collection = \Drupal::service('keyvalue')->get(GATE1_STEP05_STATE_COLLECTION);
  $collection->delete(GATE1_STEP05_STATE_KEY);
  $collection->delete(GATE1_STEP05_ARTIFACT_KEY);
  gate1_step05_delete_agent_config();
  return ['schema_version' => 1, 'status' => 'cleared', 'provider_request_count' => 0];
}

try {
  $result = match ($mode) {
    'preflight' => gate1_step05_preflight(),
    'start' => gate1_step05_start($run_id_argument),
    'resume' => gate1_step05_resume(),
    'status' => gate1_step05_status(),
    'export' => gate1_step05_export(),
    'snapshot' => gate1_step05_snapshot(),
    'clear-state' => gate1_step05_clear_state(),
    default => throw new InvalidArgumentException(
      'Usage: preflight | start RUN_ID | resume | status | export | snapshot | clear-state',
    ),
  };
  gate1_step05_emit($result);
}
catch (Throwable $exception) {
  fwrite(STDERR, sprintf("[ERROR] %s: %s\n", $exception::class, $exception->getMessage()));
  exit(1);
}
