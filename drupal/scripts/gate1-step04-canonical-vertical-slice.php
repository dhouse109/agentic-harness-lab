<?php

declare(strict_types=1);

use Drupal\ai\Event\PreGenerateResponseEvent;
use Drupal\agentic_harness_drupal_ai\Service\FileEntityResolver;
use Drupal\ai_agents\Event\AgentRequestEvent;
use Drupal\ai_agents\Task\Task;
use Drupal\Core\Config\Entity\ConfigEntityInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

/**
 * Gate 1 Step 1.04 Drupal AI canonical vertical slice.
 */

const GATE1_STEP04_MODEL = 'gpt-4.1-mini-2025-04-14';
const GATE1_STEP04_PROVIDER = 'openai';
const GATE1_STEP04_TEMPERATURE = 0.0;
const GATE1_STEP04_PROMPT_VERSION = 'drupal-ai-alt-text-v1.0.0';
const GATE1_STEP04_VALIDATOR_VERSION = 'gate05-validator-1.0.0';
const GATE1_STEP04_TARGET_SHA256 = '1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728';
const GATE1_STEP04_SOURCE_SHA256 = 'f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17';
const GATE1_STEP04_STATE_COLLECTION = 'agentic_harness_drupal_ai.run_state';
const GATE1_STEP04_STATE_KEY = 'canonical_slice.active';
const GATE1_STEP04_ARTIFACT_KEY = 'canonical_slice.artifacts';
const GATE1_STEP04_LOCK = 'agentic_harness_drupal_ai.canonical_slice';
const GATE1_STEP04_AGENT_ID = 'agentic_harness_alt_text_canonical_slice';
const GATE1_STEP04_TEMPLATE_AGENT_ID = 'content_type_agent_triage';

/** @var array<int, mixed> $extra */
$arguments = is_array($extra ?? NULL) ? $extra : [];
$mode = (string) ($arguments[0] ?? '');
$run_id_argument = (string) ($arguments[1] ?? '');

function gate1_step04_emit(array $value): void {
  print json_encode(
    $value,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ) . PHP_EOL;
}

function gate1_step04_now(): string {
  return gmdate('Y-m-d\TH:i:s\Z');
}

function gate1_step04_sort(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate1_step04_sort', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate1_step04_sort($item);
  }
  return $value;
}

function gate1_step04_json(mixed $value): string {
  return json_encode(
    gate1_step04_sort($value),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );
}

function gate1_step04_sha(mixed $value): string {
  return hash('sha256', gate1_step04_json($value));
}

function gate1_step04_file_resolver(): FileEntityResolver {
  $container = \Drupal::getContainer();
  return new FileEntityResolver(
    $container->get('entity_type.manager'),
    $container->get('file_system'),
  );
}

function gate1_step04_user(string $name): UserInterface {
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
function gate1_step04_adapter(string $plugin_id, ?string $input_name = NULL, mixed $input = NULL): array {
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
 * Returns the frozen ordered target list from the discovery adapter envelope.
 *
 * @return array<int, array<string, mixed>>
 */
function gate1_step04_discover_targets(): array {
  $data = gate1_step04_adapter('discover_targets')['data'];

  if (
    array_is_list($data)
    || !array_key_exists('targets', $data)
    || !array_key_exists('total_count', $data)
    || !is_array($data['targets'])
    || !array_is_list($data['targets'])
    || !is_int($data['total_count'])
  ) {
    throw new RuntimeException(
      'Discovery adapter data does not match the frozen envelope.',
    );
  }

  $targets = $data['targets'];
  if ($data['total_count'] !== count($targets)) {
    throw new RuntimeException(
      'Discovery adapter total_count differs from its target list.',
    );
  }

  return $targets;
}

/**
 * Returns the sanitized current seeded-state projection.
 *
 * @return array<string, mixed>
 */
function gate1_step04_snapshot(): array {
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
    $current_user->setAccount(gate1_step04_user('agent_bot'));
    $targets = $container->get('agentic_harness_tools.image_review_finder')->find();
  }
  finally {
    $current_user->setAccount($original);
  }

  $collection = $container->get('keyvalue')->get(GATE1_STEP04_STATE_COLLECTION);
  $state_present = $collection->get(GATE1_STEP04_STATE_KEY) !== NULL
    || $collection->get(GATE1_STEP04_ARTIFACT_KEY) !== NULL;
  $agent_present = $container->get('entity_type.manager')
    ->getStorage('ai_agent')
    ->load(GATE1_STEP04_AGENT_ID) instanceof ConfigEntityInterface;

  $target_hash = gate1_step04_sha($targets);
  $source_hash = gate1_step04_sha($articles);

  return [
    'schema_version' => 1,
    'article_count' => count($articles),
    'suggestion_count' => $suggestion_count,
    'target_count' => count($targets),
    'canonical_target_sequence' => $targets[0]['sequence'] ?? NULL,
    'target_sequence_sha256' => $target_hash,
    'article_source_sha256' => $source_hash,
    'runtime_state_present' => $state_present,
    'temporary_agent_config_present' => $agent_present,
    'seeded_clean' => count($articles) === 20
      && $suggestion_count === 0
      && count($targets) === 12
      && ($targets[0]['sequence'] ?? NULL) === 1
      && $target_hash === GATE1_STEP04_TARGET_SHA256
      && $source_hash === GATE1_STEP04_SOURCE_SHA256
      && !$state_present
      && !$agent_present,
  ];
}

/**
 * Creates a repository-owned temporary AI Agent config by narrowing a pinned template.
 *
 * @return array<string, mixed>
 */
function gate1_step04_create_agent_config(string $system_prompt): array {
  $storage = \Drupal::entityTypeManager()->getStorage('ai_agent');
  if ($storage->load(GATE1_STEP04_AGENT_ID) instanceof ConfigEntityInterface) {
    throw new RuntimeException('Temporary canonical-slice AI Agent configuration already exists.');
  }
  $template = $storage->load(GATE1_STEP04_TEMPLATE_AGENT_ID);
  if (!$template instanceof ConfigEntityInterface) {
    throw new RuntimeException('Pinned AI Agent template is unavailable.');
  }

  $data = $template->toArray();
  $required_keys = [
    'id',
    'label',
    'description',
    'system_prompt',
    'max_loops',
    'default_information_tools',
    'structured_output_enabled',
    'structured_output_schema',
    'tools',
    'tool_settings',
    'tool_usage_limits',
  ];
  foreach ($required_keys as $required_key) {
    if (!array_key_exists($required_key, $data)) {
      throw new RuntimeException('Pinned AI Agent template lacks required config key: ' . $required_key);
    }
  }

  unset($data['uuid']);
  $data['id'] = GATE1_STEP04_AGENT_ID;
  $data['label'] = 'Agentic Harness Alt Text Canonical Slice';
  $data['description'] = 'One-target Gate 1 Step 1.04 execution configuration.';
  $data['system_prompt'] = $system_prompt;
  if (array_key_exists('secured_system_prompt', $data)) {
    $data['secured_system_prompt'] = $system_prompt;
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
  $data['structured_output_schema'] = json_encode([
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
  $data['tools'] = [];
  $data['tool_settings'] = [];
  $data['tool_usage_limits'] = [];

  $entity = $storage->create($data);
  if (!$entity instanceof ConfigEntityInterface) {
    throw new RuntimeException('Drupal did not create the canonical-slice AI Agent configuration.');
  }
  $entity->save();
  \Drupal::service('plugin.manager.ai_agents')->clearCachedDefinitions();

  $saved = $storage->load(GATE1_STEP04_AGENT_ID);
  if (!$saved instanceof ConfigEntityInterface) {
    throw new RuntimeException('Saved canonical-slice AI Agent configuration could not be reloaded.');
  }
  $saved_data = $saved->toArray();
  if (
    ($saved_data['system_prompt'] ?? NULL) !== $system_prompt
    || ($saved_data['structured_output_enabled'] ?? NULL) !== TRUE
    || ($saved_data['structured_output_schema'] ?? NULL) !== $data['structured_output_schema']
    || ($saved_data['tools'] ?? NULL) !== []
    || ($saved_data['tool_settings'] ?? NULL) !== []
    || ($saved_data['tool_usage_limits'] ?? NULL) !== []
    || (int) ($saved_data['max_loops'] ?? 0) !== 1
  ) {
    throw new RuntimeException('Saved canonical-slice AI Agent configuration differs from the controlled design.');
  }

  return [
    'id' => $entity->id(),
    'label' => $entity->label(),
    'system_prompt_sha256' => hash('sha256', $system_prompt),
    'structured_output_schema_sha256' => hash('sha256', (string) $data['structured_output_schema']),
    'structured_output_enabled' => TRUE,
    'tool_count' => 0,
    'tool_settings_count' => 0,
    'tool_usage_limits_count' => 0,
    'max_loops' => 1,
    'template_id' => GATE1_STEP04_TEMPLATE_AGENT_ID,
  ];
}

function gate1_step04_delete_agent_config(): void {
  $storage = \Drupal::entityTypeManager()->getStorage('ai_agent');
  $entity = $storage->load(GATE1_STEP04_AGENT_ID);
  if ($entity instanceof ConfigEntityInterface) {
    $entity->delete();
    \Drupal::service('plugin.manager.ai_agents')->clearCachedDefinitions();
  }
}

/**
 * @return array<string, mixed>
 */
function gate1_step04_safe_checkpoint(object $agent): array {
  $checkpoint = $agent->toArray();
  $encoded = gate1_step04_json($checkpoint);
  if (
    !empty($checkpoint['chat_history'])
    || preg_match('/(?:data:image|Authorization\s*:|Bearer\s+|sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9+\/]{128,}={0,2})/i', $encoded) === 1
  ) {
    throw new RuntimeException('Pre-image wrapper checkpoint contains prohibited material.');
  }

  $restored = \Drupal::service('plugin.manager.ai_agents')->createInstance(GATE1_STEP04_AGENT_ID);
  $restored->fromArray($checkpoint);
  if (
    $restored->getModelName() !== GATE1_STEP04_MODEL
    || $restored->getAiConfiguration() !== ['temperature' => GATE1_STEP04_TEMPERATURE]
  ) {
    throw new RuntimeException('Safe wrapper checkpoint could not be restored.');
  }

  return [
    'stage' => 'pre_task_pre_image_pre_provider',
    'provider_id' => $checkpoint['provider_id'] ?? GATE1_STEP04_PROVIDER,
    'model_name' => $checkpoint['model_name'] ?? GATE1_STEP04_MODEL,
    'ai_configuration' => $checkpoint['ai_configuration'] ?? ['temperature' => GATE1_STEP04_TEMPERATURE],
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
function gate1_step04_model_output(object $agent, string $solved): array {
  $candidate = $agent->getStructuredOutput();
  if (is_array($candidate) && isset($candidate['proposed_alt_text'])) {
    $output = $candidate;
  }
  else {
    $decoded = json_decode(trim($solved), TRUE);
    if (!is_array($decoded)) {
      throw new RuntimeException('AI Agent output was not a structured JSON object.');
    }
    $output = $decoded;
  }

  $keys = array_keys($output);
  sort($keys);
  if (
    $keys !== ['proposed_alt_text']
    || !is_string($output['proposed_alt_text'])
    || trim($output['proposed_alt_text']) === ''
    || mb_strlen(trim($output['proposed_alt_text'])) > 250
  ) {
    throw new RuntimeException('AI Agent output does not conform to the frozen model-output schema.');
  }
  return ['proposed_alt_text' => trim($output['proposed_alt_text'])];
}

function gate1_step04_expect_resolver_failure(array $context): void {
  try {
    gate1_step04_file_resolver()->resolve($context);
  }
  catch (RuntimeException) {
    return;
  }
  throw new RuntimeException('A declared File resolver negative control unexpectedly passed.');
}

/**
 * @return array<string, mixed>
 */
function gate1_step04_preflight(): array {
  $container = \Drupal::getContainer();
  $snapshot = gate1_step04_snapshot();
  if (!$snapshot['seeded_clean']) {
    throw new RuntimeException('Preflight requires seeded-clean state inside its reset boundary.');
  }

  $provider_requests = 0;
  $agent_requests = 0;
  $container->get('event_dispatcher')->addListener(
    PreGenerateResponseEvent::EVENT_NAME,
    static function () use (&$provider_requests): void {
      $provider_requests++;
      throw new RuntimeException('Provider request prohibited during Step 1.04 preflight.');
    },
    10000,
  );
  $container->get('event_dispatcher')->addListener(
    AgentRequestEvent::EVENT_NAME,
    static function () use (&$agent_requests): void {
      $agent_requests++;
      throw new RuntimeException('AI Agent request prohibited during Step 1.04 preflight.');
    },
    10000,
  );

  $current_user = $container->get('current_user');
  $original = $current_user->getAccount();
  $agent_created = FALSE;
  try {
    $current_user->setAccount(gate1_step04_user('agent_bot'));
    $targets = gate1_step04_discover_targets();
    if (count($targets) !== 12 || ($targets[0]['sequence'] ?? NULL) !== 1) {
      throw new RuntimeException('Preflight discovery differs from the frozen sequence.');
    }
    $context = gate1_step04_adapter('get_image_context', 'target', $targets[0])['data'];
    $file = gate1_step04_file_resolver()->resolve($context);
    if (!$file instanceof FileInterface || $file->uuid() !== $context['image']['file_uuid']) {
      throw new RuntimeException('Preflight File resolver did not return the authorized entity.');
    }

    $negative_count = 0;
    foreach (['filename', 'mime_type', 'byte_length', 'sha256'] as $field) {
      $bad = $context;
      $bad['image'][$field] = match ($field) {
        'filename' => 'mismatch-' . $bad['image'][$field],
        'mime_type' => 'image/x-mismatch',
        'byte_length' => $bad['image'][$field] + 1,
        'sha256' => str_repeat('0', 64),
      };
      gate1_step04_expect_resolver_failure($bad);
      $negative_count++;
    }
    $bad = $context;
    $bad['image']['file_uuid'] = '00000000-0000-4000-8000-000000000000';
    gate1_step04_expect_resolver_failure($bad);
    $negative_count++;
    $bad = $context;
    $bad['image']['uri'] = 'https://example.invalid/image.png';
    gate1_step04_expect_resolver_failure($bad);
    $negative_count++;

    $system_prompt = gate1_step04_system_prompt();
    $config = gate1_step04_create_agent_config($system_prompt);
    $agent_created = TRUE;
    $agent = $container->get('plugin.manager.ai_agents')->createInstance(GATE1_STEP04_AGENT_ID);
    foreach (['setAiProvider', 'setModelName', 'setAiConfiguration', 'overrideFunctions', 'getFunctions', 'toArray', 'fromArray', 'setTask', 'determineSolvability', 'solve', 'getStructuredOutput'] as $method) {
      if (!method_exists($agent, $method)) {
        throw new RuntimeException('Pinned AI Agent wrapper lacks required method: ' . $method);
      }
    }
    $provider = $container->get('ai.provider')->createInstance(GATE1_STEP04_PROVIDER);
    $provider->setConfiguration(['temperature' => GATE1_STEP04_TEMPERATURE]);
    $agent->setAiProvider($provider);
    $agent->setModelName(GATE1_STEP04_MODEL);
    $agent->setAiConfiguration(['temperature' => GATE1_STEP04_TEMPERATURE]);
    $agent->overrideFunctions(['tools' => [], 'tool_usage_limits' => [], 'tool_settings' => []]);
    $functions = $agent->getFunctions();
    if (!empty($functions['normalized']) || !empty($functions['executable'])) {
      throw new RuntimeException('Preflight AI Agent exposes model-callable tools.');
    }
    $checkpoint = gate1_step04_safe_checkpoint($agent);

    $key_reference = (string) $container->get('config.factory')
      ->get('ai_provider_openai.settings')
      ->get('api_key');
    if ($key_reference === '') {
      throw new RuntimeException('OpenAI provider key reference is not configured.');
    }

    return [
      'schema_version' => 1,
      'status' => 'pass',
      'snapshot' => $snapshot,
      'canonical_target_sequence' => 1,
      'target_count' => 12,
      'file_identity_verified' => TRUE,
      'file_uuid' => $file->uuid(),
      'file_negative_controls_rejected' => $negative_count,
      'uri_or_path_retained' => FALSE,
      'raw_image_retained' => FALSE,
      'temporary_agent_configuration' => $config,
      'safe_wrapper_checkpoint' => $checkpoint,
      'model_callable_tool_count' => 0,
      'configured_key_reference_present' => TRUE,
      'configured_key_value_retained' => FALSE,
      'provider_request_count' => $provider_requests,
      'agent_request_count' => $agent_requests,
      'model_call_performed' => FALSE,
      'network_call_performed' => FALSE,
    ];
  }
  finally {
    if ($agent_created) {
      gate1_step04_delete_agent_config();
    }
    $current_user->setAccount($original);
  }
}

function gate1_step04_system_prompt(): string {
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
function gate1_step04_user_prompt(array $target, array $context): string {
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
 * @return array<string, mixed>
 */
function gate1_step04_start(string $run_id): array {
  if (preg_match('/^drupal_ai-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$/', $run_id) !== 1) {
    throw new RuntimeException('Run ID does not conform to the frozen Drupal AI pattern.');
  }

  $container = \Drupal::getContainer();
  $lock = $container->get('lock.persistent');
  if (!$lock->acquire(GATE1_STEP04_LOCK, 900.0)) {
    throw new RuntimeException('Canonical-slice run lock is unavailable.');
  }

  $current_user = $container->get('current_user');
  $original_account = $current_user->getAccount();
  $collection = $container->get('keyvalue')->get(GATE1_STEP04_STATE_COLLECTION);
  $agent_created = FALSE;

  try {
    if ($collection->get(GATE1_STEP04_STATE_KEY) !== NULL) {
      throw new RuntimeException('Canonical-slice runtime state already exists.');
    }
    $before = gate1_step04_snapshot();
    if (!$before['seeded_clean']) {
      throw new RuntimeException('Drupal is not at the seeded-clean Step 1.04 boundary.');
    }

    $current_user->setAccount(gate1_step04_user('agent_bot'));
    $targets = gate1_step04_discover_targets();
    if (count($targets) !== 12 || ($targets[0]['sequence'] ?? NULL) !== 1) {
      throw new RuntimeException('Discovery did not return the frozen canonical target sequence.');
    }
    $target = $targets[0];
    $context = gate1_step04_adapter('get_image_context', 'target', $target)['data'];
    $file = gate1_step04_file_resolver()->resolve($context);
    if (!$file instanceof FileInterface) {
      throw new RuntimeException('File resolver did not return FileInterface.');
    }

    $agent_config = gate1_step04_create_agent_config(gate1_step04_system_prompt());
    $agent_created = TRUE;
    $agent = $container->get('plugin.manager.ai_agents')->createInstance(GATE1_STEP04_AGENT_ID);
    foreach (['setAiProvider', 'setModelName', 'setAiConfiguration', 'overrideFunctions', 'getFunctions', 'toArray', 'fromArray', 'setTask', 'determineSolvability', 'solve', 'getStructuredOutput'] as $method) {
      if (!method_exists($agent, $method)) {
        throw new RuntimeException('Pinned AI Agent wrapper lacks required method: ' . $method);
      }
    }
    $provider = $container->get('ai.provider')->createInstance(GATE1_STEP04_PROVIDER);
    $provider->setConfiguration(['temperature' => GATE1_STEP04_TEMPERATURE]);
    $agent->setAiProvider($provider);
    $agent->setModelName(GATE1_STEP04_MODEL);
    $agent->setAiConfiguration(['temperature' => GATE1_STEP04_TEMPERATURE]);
    $agent->overrideFunctions(['tools' => [], 'tool_usage_limits' => [], 'tool_settings' => []]);
    $functions = $agent->getFunctions();
    if (!empty($functions['normalized']) || !empty($functions['executable'])) {
      throw new RuntimeException('Canonical-slice AI Agent unexpectedly exposes model-callable tools.');
    }

    $checkpoint = gate1_step04_safe_checkpoint($agent);
    $task = new Task(gate1_step04_user_prompt($target, $context));
    $task->setFiles([$file]);
    $agent->setTask($task);

    $provider_requests = 0;
    $agent_requests = 0;
    $container->get('event_dispatcher')->addListener(
      PreGenerateResponseEvent::EVENT_NAME,
      static function () use (&$provider_requests): void {
        $provider_requests++;
        if ($provider_requests > 1) {
          throw new RuntimeException('Second provider request blocked by Step 1.04 one-call guard.');
        }
      },
      10000,
    );
    $container->get('event_dispatcher')->addListener(
      AgentRequestEvent::EVENT_NAME,
      static function () use (&$agent_requests): void {
        $agent_requests++;
        if ($agent_requests > 1) {
          throw new RuntimeException('Second AI Agent request blocked by Step 1.04 one-call guard.');
        }
      },
      10000,
    );

    $started = gate1_step04_now();
    $state = [
      'schema_version' => 1,
      'run_id' => $run_id,
      'framework_origin' => 'drupal_ai',
      'status' => 'running',
      'provider' => GATE1_STEP04_PROVIDER,
      'model' => GATE1_STEP04_MODEL,
      'temperature' => GATE1_STEP04_TEMPERATURE,
      'prompt_version' => GATE1_STEP04_PROMPT_VERSION,
      'target_sequence_hash' => 'sha256:' . GATE1_STEP04_TARGET_SHA256,
      'canonical_target' => $target,
      'model_call_count' => 0,
      'recommendation_identity' => NULL,
      'wrapper_checkpoint' => $checkpoint,
      'started_at' => $started,
      'updated_at' => $started,
      'human_review_paused_at' => NULL,
      'resumed_at' => NULL,
      'completed_at' => NULL,
      'failed_at' => NULL,
      'aborted_at' => NULL,
    ];
    $collection->set(GATE1_STEP04_STATE_KEY, $state);

    $agent->determineSolvability();
    $solved = (string) $agent->solve();
    if ($provider_requests !== 1 || $agent_requests !== 1) {
      throw new RuntimeException('Canonical-slice execution did not make exactly one agent/provider request.');
    }
    $model_output = gate1_step04_model_output($agent, $solved);

    $evidence_payload = [
      'schema_version' => 1,
      'target' => $target,
      'context_evidence_hash' => $context['evidence_hash'],
      'article_title_sha256' => gate1_step04_sha($context['article']['title']),
      'article_body_sha256' => gate1_step04_sha($context['article']['body_plain']),
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
      'provider' => GATE1_STEP04_PROVIDER,
      'model' => GATE1_STEP04_MODEL,
      'temperature' => GATE1_STEP04_TEMPERATURE,
      'provider_request_count' => $provider_requests,
    ];
    $recommendation = [
      'schema_version' => 1,
      'target' => $target,
      'proposed_alt_text' => $model_output['proposed_alt_text'],
      'source_framework' => 'drupal_ai',
      'run_id' => $run_id,
      'evidence_hash' => 'sha256:' . gate1_step04_sha($evidence_payload),
      'validator_version' => GATE1_STEP04_VALIDATOR_VERSION,
    ];

    $validated = $container->get('agentic_harness_tools.recommendation_validator')->validate($recommendation);
    $recommendation = $validated['recommendation'];

    $submission = gate1_step04_adapter('submit_recommendation', 'recommendation', $recommendation)['data'];
    $replay = gate1_step04_adapter('submit_recommendation', 'recommendation', $recommendation)['data'];
    foreach (['node_id', 'uuid', 'revision_id'] as $identity_key) {
      if (($submission[$identity_key] ?? NULL) !== ($replay[$identity_key] ?? NULL)) {
        throw new RuntimeException('Submission idempotent replay identity changed.');
      }
    }

    $pending = gate1_step04_adapter(
      'get_recommendation_status',
      'recommendation_id',
      (string) $submission['uuid'],
    )['data'];
    if (($pending['status'] ?? NULL) !== 'pending') {
      throw new RuntimeException('Submitted recommendation did not enter pending human review.');
    }
    $pending_observed_at = gate1_step04_now();

    $paused = gate1_step04_now();
    $state['status'] = 'awaiting_human_review';
    $state['model_call_count'] = 1;
    $state['recommendation_identity'] = [
      'node_id' => $submission['node_id'],
      'uuid' => $submission['uuid'],
      'revision_id' => $submission['revision_id'],
      'run_id' => $run_id,
      'target_sequence' => 1,
    ];
    $state['updated_at'] = $paused;
    $state['human_review_paused_at'] = $paused;
    $collection->set(GATE1_STEP04_STATE_KEY, $state);

    $lifecycle = [
      'canonical_targets' => [$target],
      'model_outputs' => [$model_output],
      'recommendations' => [$recommendation],
      'validation_results' => [[
        'sequence' => 1,
        'target' => $target,
        'structured_output_schema_valid' => TRUE,
        'deterministic_validation_passed' => TRUE,
        'errors' => [],
      ]],
      'submissions' => [[
        'sequence' => 1,
        'target' => $target,
        'node_id' => $submission['node_id'],
        'uuid' => $submission['uuid'],
        'revision_id' => $submission['revision_id'],
        'initial_status' => 'pending',
        'idempotent_replay_same_identity' => TRUE,
      ]],
      'statuses' => [[
        'recommendation_uuid' => $pending['uuid'],
        'revision_id' => $pending['revision_id'],
        'status' => 'pending',
        'observed_at' => $pending_observed_at,
      ]],
      'human_review' => [],
    ];
    $supplemental = [
      'schema_version' => 1,
      'authorized_context' => [
        'target_sequence' => 1,
        'article_revision_id' => $context['article']['revision_id'],
        'content_language' => $context['article']['content_language'] ?? NULL,
        'article_title_sha256' => $evidence_payload['article_title_sha256'],
        'article_body_sha256' => $evidence_payload['article_body_sha256'],
        'existing_alt_present' => $context['existing_alt'] !== NULL && $context['existing_alt'] !== '',
        'image' => $evidence_payload['image'],
        'evidence_hash' => $context['evidence_hash'],
        'collected_at' => $context['collected_at'],
      ],
      'file_resolution' => [
        'status' => 'pass',
        'identity_fields_verified' => ['file_uuid', 'filename', 'mime_type', 'byte_length', 'sha256'],
        'approved_local_stream_wrapper' => TRUE,
        'remote_uri_rejected' => TRUE,
        'model_supplied_locator_rejected' => TRUE,
        'uri_retained' => FALSE,
        'resolved_path_retained' => FALSE,
        'file_entity_retained' => FALSE,
        'raw_bytes_retained' => FALSE,
      ],
      'agent_configuration' => $agent_config,
      'wrapper_checkpoint' => $checkpoint,
      'provider_boundary' => [
        'provider_request_count' => $provider_requests,
        'agent_request_event_count' => $agent_requests,
        'maximum_provider_requests' => 1,
        'automatic_retries' => 0,
        'model_callable_tool_count' => 0,
        'required_tool_loop' => FALSE,
      ],
      'source_article_sha256_before' => $before['article_source_sha256'],
      'raw_image_retained' => FALSE,
      'post_image_wrapper_serialization_performed' => FALSE,
      'step_1_05_started' => FALSE,
    ];
    $collection->set(GATE1_STEP04_ARTIFACT_KEY, [
      'lifecycle' => $lifecycle,
      'supplemental' => $supplemental,
    ]);

    return [
      'schema_version' => 1,
      'status' => 'awaiting_human_review',
      'run_id' => $run_id,
      'provider_request_count' => $provider_requests,
      'agent_request_count' => $agent_requests,
      'automatic_retries' => 0,
      'recommendation' => $state['recommendation_identity'] + [
        'proposed_alt_text' => $model_output['proposed_alt_text'],
      ],
      'pending_status' => $pending,
      'state' => $state,
      'lifecycle' => $lifecycle,
      'supplemental' => $supplemental,
      'human_action_required' => 'Approve this recommendation as editor_dana, then run resume.',
      'raw_image_retained' => FALSE,
      'post_image_wrapper_serialization_performed' => FALSE,
      'step_1_05_started' => FALSE,
    ];
  }
  catch (Throwable $exception) {
    $now = gate1_step04_now();
    $state = $collection->get(GATE1_STEP04_STATE_KEY);
    if (is_array($state)) {
      $state['status'] = 'failed';
      $state['updated_at'] = $now;
      $state['failed_at'] = $now;
      $collection->set(GATE1_STEP04_STATE_KEY, $state);
    }
    if ($agent_created) {
      gate1_step04_delete_agent_config();
    }
    throw $exception;
  }
  finally {
    $current_user->setAccount($original_account);
    $lock->release(GATE1_STEP04_LOCK);
  }
}

/**
 * @return array<string, mixed>
 */
function gate1_step04_status(): array {
  $container = \Drupal::getContainer();
  $collection = $container->get('keyvalue')->get(GATE1_STEP04_STATE_COLLECTION);
  $state = $collection->get(GATE1_STEP04_STATE_KEY);
  if (!is_array($state)) {
    return ['schema_version' => 1, 'status' => 'not_started', 'provider_request_count' => 0];
  }

  $result = ['schema_version' => 1, 'state' => $state, 'provider_request_count' => 0];
  if (is_array($state['recommendation_identity'] ?? NULL)) {
    $current_user = $container->get('current_user');
    $original = $current_user->getAccount();
    try {
      $current_user->setAccount(gate1_step04_user('agent_bot'));
      $result['recommendation_status'] = gate1_step04_adapter(
        'get_recommendation_status',
        'recommendation_id',
        (string) $state['recommendation_identity']['uuid'],
      )['data'];
    }
    finally {
      $current_user->setAccount($original);
    }
  }
  return $result;
}

/**
 * @return array<string, mixed>
 */
function gate1_step04_resume(): array {
  $container = \Drupal::getContainer();
  $lock = $container->get('lock.persistent');
  if (!$lock->acquire(GATE1_STEP04_LOCK, 300.0)) {
    throw new RuntimeException('Canonical-slice run lock is unavailable.');
  }

  $current_user = $container->get('current_user');
  $original_account = $current_user->getAccount();
  $collection = $container->get('keyvalue')->get(GATE1_STEP04_STATE_COLLECTION);
  $provider_requests = 0;
  $agent_requests = 0;
  $container->get('event_dispatcher')->addListener(
    PreGenerateResponseEvent::EVENT_NAME,
    static function () use (&$provider_requests): void {
      $provider_requests++;
      throw new RuntimeException('Provider request prohibited during Step 1.04 resume.');
    },
    10000,
  );
  $container->get('event_dispatcher')->addListener(
    AgentRequestEvent::EVENT_NAME,
    static function () use (&$agent_requests): void {
      $agent_requests++;
      throw new RuntimeException('AI Agent request prohibited during Step 1.04 resume.');
    },
    10000,
  );

  try {
    $state = $collection->get(GATE1_STEP04_STATE_KEY);
    $artifacts = $collection->get(GATE1_STEP04_ARTIFACT_KEY);
    if (!is_array($state) || !is_array($artifacts)) {
      throw new RuntimeException('Canonical-slice runtime state is unavailable.');
    }
    if (($state['status'] ?? NULL) !== 'awaiting_human_review') {
      throw new RuntimeException('Canonical-slice run is not awaiting human review.');
    }
    if (($state['model_call_count'] ?? NULL) !== 1) {
      throw new RuntimeException('Canonical-slice model-call count is invalid before resume.');
    }
    if (!is_array($artifacts['lifecycle'] ?? NULL) || !is_array($artifacts['supplemental'] ?? NULL)) {
      throw new RuntimeException('Canonical-slice artifacts are malformed.');
    }

    $current_user->setAccount(gate1_step04_user('agent_bot'));
    $identifier = (string) ($state['recommendation_identity']['uuid'] ?? '');
    $approved = gate1_step04_adapter('get_recommendation_status', 'recommendation_id', $identifier)['data'];
    if (($approved['status'] ?? NULL) !== 'approved') {
      throw new RuntimeException('Recommendation has not been approved.');
    }
    if (($approved['reviewer_username'] ?? NULL) !== 'editor_dana') {
      throw new RuntimeException('Recommendation approval was not performed by editor_dana.');
    }
    if (($approved['uuid'] ?? NULL) !== $identifier) {
      throw new RuntimeException('Approved recommendation identity changed.');
    }
    if ($provider_requests !== 0 || $agent_requests !== 0) {
      throw new RuntimeException('Resume crossed the prohibited agent/provider boundary.');
    }

    $source_at_resume = gate1_step04_snapshot()['article_source_sha256'];
    if ($source_at_resume !== GATE1_STEP04_SOURCE_SHA256) {
      throw new RuntimeException('Source Article projection changed before resume.');
    }

    $observed_at = gate1_step04_now();
    $lifecycle = $artifacts['lifecycle'];
    $prior_submission = $lifecycle['submissions'][0] ?? NULL;
    if (!is_array($prior_submission)) {
      throw new RuntimeException('Prior submission evidence is unavailable.');
    }
    $lifecycle['statuses'][] = [
      'recommendation_uuid' => $approved['uuid'],
      'revision_id' => $approved['revision_id'],
      'status' => 'approved',
      'observed_at' => $observed_at,
    ];
    $lifecycle['human_review'][] = [
      'recommendation_uuid' => $approved['uuid'],
      'prior_revision_id' => $prior_submission['revision_id'],
      'decision_revision_id' => $approved['revision_id'],
      'reviewer' => 'editor_dana',
      'decision' => 'approved',
      'reviewed_at' => $approved['reviewed_at'],
      'source_article_unchanged' => TRUE,
    ];

    $now = gate1_step04_now();
    $state['status'] = 'resuming';
    $state['updated_at'] = $now;
    $state['resumed_at'] = $now;
    $collection->set(GATE1_STEP04_STATE_KEY, $state);

    $completed = gate1_step04_now();
    $state['status'] = 'completed';
    $state['updated_at'] = $completed;
    $state['completed_at'] = $completed;
    $artifacts['lifecycle'] = $lifecycle;
    $artifacts['supplemental']['source_article_sha256_at_resume'] = $source_at_resume;
    $artifacts['supplemental']['provider_request_count_resume'] = $provider_requests;
    $artifacts['supplemental']['agent_request_count_resume'] = $agent_requests;
    $collection->set(GATE1_STEP04_STATE_KEY, $state);
    $collection->set(GATE1_STEP04_ARTIFACT_KEY, $artifacts);

    return [
      'schema_version' => 1,
      'status' => 'completed',
      'run_id' => $state['run_id'],
      'provider_request_count' => $provider_requests,
      'agent_request_count' => $agent_requests,
      'model_call_count_total' => 1,
      'approved_status' => $approved,
      'state' => $state,
      'lifecycle' => $lifecycle,
      'supplemental' => $artifacts['supplemental'],
      'step_1_05_started' => FALSE,
    ];
  }
  finally {
    $current_user->setAccount($original_account);
    $lock->release(GATE1_STEP04_LOCK);
  }
}

function gate1_step04_clear_state(): array {
  $collection = \Drupal::service('keyvalue')->get(GATE1_STEP04_STATE_COLLECTION);
  $collection->delete(GATE1_STEP04_STATE_KEY);
  $collection->delete(GATE1_STEP04_ARTIFACT_KEY);
  gate1_step04_delete_agent_config();
  return ['schema_version' => 1, 'status' => 'cleared', 'provider_request_count' => 0];
}

try {
  $result = match ($mode) {
    'preflight' => gate1_step04_preflight(),
    'start' => gate1_step04_start($run_id_argument),
    'status' => gate1_step04_status(),
    'resume' => gate1_step04_resume(),
    'clear-state' => gate1_step04_clear_state(),
    'snapshot' => gate1_step04_snapshot(),
    default => throw new InvalidArgumentException(
      'Usage: preflight | start RUN_ID | status | resume | clear-state | snapshot',
    ),
  };
  gate1_step04_emit($result);
}
catch (Throwable $exception) {
  fwrite(STDERR, sprintf("[ERROR] %s: %s\n", $exception::class, $exception->getMessage()));
  exit(1);
}
