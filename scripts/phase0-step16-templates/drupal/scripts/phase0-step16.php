<?php

declare(strict_types=1);

/**
 * Phase 0 Step 16: deterministic fixture extraction and Drupal AI capability spike.
 *
 * Run from the Drupal project root through the shell runner. This helper never
 * creates suggestion records and never changes Article fields.
 */

use Drupal\ai\OperationType\Chat\ChatInput;
use Drupal\ai\OperationType\Chat\ChatMessage;
use Drupal\ai\OperationType\Chat\Tools\ToolsInput;
use Drupal\ai\OperationType\GenericType\ImageFile;
use Drupal\Component\Utility\Html;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;

const STEP16_HELPER_VERSION = '1.0.2';
const STEP16_ARTICLE_TITLE = 'Phase 0 01 — Emergency Preparedness Checklist';
const STEP16_FIELD = 'field_image';
const STEP16_DELTA = 0;

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? '';
$runtime_dir = $args[1] ?? '';
$model_id = $args[2] ?? '';

if (!in_array($mode, ['inspect', 'extract', 'snapshot', 'vision', 'tool'], TRUE)) {
  step16_fail('Usage: phase0-step16.php -- inspect|extract|snapshot|vision|tool <runtime-dir> [model-id]');
}

try {
  match ($mode) {
    'inspect' => step16_inspect(),
    'extract' => step16_extract($runtime_dir),
    'snapshot' => step16_snapshot(),
    'vision' => step16_vision($runtime_dir, $model_id),
    'tool' => step16_tool($model_id),
  };
}
catch (Throwable $e) {
  step16_fail(sprintf('%s: %s', get_class($e), step16_sanitize($e->getMessage())));
}

/**
 * Emits a successful JSON object.
 *
 * @param array<string, mixed> $data
 */
function step16_emit(array $data): void {
  $data = ['helper_version' => STEP16_HELPER_VERSION] + $data;
  print json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . PHP_EOL;
}

function step16_fail(string $message): never {
  fwrite(STDERR, '[ERROR] ' . step16_sanitize($message) . PHP_EOL);
  exit(1);
}

function step16_sanitize(string $value): string {
  $value = preg_replace('/sk-[A-Za-z0-9_-]{8,}/', '<redacted-openai-key>', $value) ?? $value;
  $value = preg_replace('/(?i)(authorization\s*:\s*(?:bearer|basic)\s+)\S+/', '$1<redacted>', $value) ?? $value;
  $value = preg_replace('/data:image\/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+\/=]+/', '<redacted-image-data-url>', $value) ?? $value;
  return $value;
}

/**
 * @return array<string, mixed>
 */
function step16_fixture(bool $copy_image = FALSE, string $runtime_dir = ''): array {
  $storage = \Drupal::entityTypeManager()->getStorage('node');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->condition('title', STEP16_ARTICLE_TITLE)
    ->execute();
  if (count($ids) !== 1) {
    step16_fail(sprintf('Expected exactly one Article titled %s; found %d.', STEP16_ARTICLE_TITLE, count($ids)));
  }

  /** @var \Drupal\node\NodeInterface $node */
  $node = $storage->load(reset($ids));
  if (!$node instanceof NodeInterface || !$node->hasField(STEP16_FIELD)) {
    step16_fail('The deterministic Article or field_image field is unavailable.');
  }
  $field = $node->get(STEP16_FIELD);
  if (!$field->offsetExists(STEP16_DELTA)) {
    step16_fail('The deterministic field_image[0] target is unavailable.');
  }
  $item = $field->get(STEP16_DELTA);
  /** @var \Drupal\file\FileInterface|null $file */
  $file = $item->entity;
  if (!$file instanceof FileInterface) {
    step16_fail('The deterministic image target does not reference a File entity.');
  }
  $path = \Drupal::service('file_system')->realpath($file->getFileUri());
  if (!is_string($path) || !is_file($path)) {
    step16_fail('The deterministic PNG cannot be resolved on disk.');
  }
  $bytes = file_get_contents($path);
  if (!is_string($bytes) || $bytes === '') {
    step16_fail('The deterministic PNG could not be read.');
  }
  $dimensions = getimagesize($path);
  if (!is_array($dimensions)) {
    step16_fail('The deterministic image dimensions could not be read.');
  }
  $body = $node->hasField('body') ? (string) $node->get('body')->value : '';
  $body_plain = trim(preg_replace('/\s+/', ' ', Html::decodeEntities(strip_tags($body))) ?? '');
  $context = [
    'article_title' => (string) $node->label(),
    'article_body_plain' => $body_plain,
  ];
  $source_state = [
    'node_uuid' => $node->uuid(),
    'revision_id' => (int) $node->getRevisionId(),
    'field_name' => STEP16_FIELD,
    'delta' => STEP16_DELTA,
    'file_uuid' => $file->uuid(),
    'file_uri' => $file->getFileUri(),
    'existing_alt' => (string) ($item->alt ?? ''),
    'image_sha256' => hash('sha256', $bytes),
    'article_title' => (string) $node->label(),
    'article_body_plain' => $body_plain,
  ];

  $fixture = [
    'sequence' => 1,
    'node_id' => (int) $node->id(),
    'node_uuid' => $node->uuid(),
    'revision_id' => (int) $node->getRevisionId(),
    'field_name' => STEP16_FIELD,
    'delta' => STEP16_DELTA,
    'file_id' => (int) $file->id(),
    'file_uuid' => $file->uuid(),
    'existing_alt' => (string) ($item->alt ?? ''),
    'article_title' => (string) $node->label(),
    'article_body_plain' => $body_plain,
    'filename' => $file->getFilename(),
    'mime_type' => $file->getMimeType(),
    'width' => (int) $dimensions[0],
    'height' => (int) $dimensions[1],
    'image_byte_length' => strlen($bytes),
    'image_sha256' => hash('sha256', $bytes),
    'context_sha256' => hash('sha256', json_encode($context, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)),
    'source_sha256' => hash('sha256', json_encode($source_state, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)),
    'suggestion_count' => step16_suggestion_count(),
    'synthetic_fixture' => TRUE,
  ];

  if ($copy_image) {
    if ($runtime_dir === '') {
      step16_fail('A runtime directory is required for fixture extraction.');
    }
    if (!is_dir($runtime_dir) && !mkdir($runtime_dir, 0700, TRUE) && !is_dir($runtime_dir)) {
      step16_fail('Could not create the runtime directory.');
    }
    $image_path = rtrim($runtime_dir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'fixture.png';
    $fixture_path = rtrim($runtime_dir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'fixture.json';
    if (file_put_contents($image_path, $bytes, LOCK_EX) === FALSE) {
      step16_fail('Could not write runtime fixture.png.');
    }
    if (file_put_contents(
      $fixture_path,
      json_encode($fixture, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . PHP_EOL,
      LOCK_EX,
    ) === FALSE) {
      step16_fail('Could not write runtime fixture.json.');
    }
    chmod($image_path, 0600);
    chmod($fixture_path, 0600);
    $fixture['runtime_image_relative'] = 'fixture.png';
    $fixture['runtime_fixture_relative'] = 'fixture.json';
  }

  return $fixture;
}

function step16_suggestion_count(): int {
  $storage = \Drupal::entityTypeManager()->getStorage('node');
  return (int) $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'alt_text_suggestion')
    ->count()
    ->execute();
}

function step16_extract(string $runtime_dir): void {
  $fixture = step16_fixture(TRUE, $runtime_dir);
  step16_emit([
    'test_id' => 'FIXTURE-001',
    'status' => 'pass',
    'fixture' => $fixture,
    'image_representation_candidate' => 'base64_data_url',
    'base64_retained' => FALSE,
  ]);
}

function step16_snapshot(): void {
  $fixture = step16_fixture(FALSE);
  step16_emit([
    'test_id' => 'MUTATION-SNAPSHOT',
    'status' => 'pass',
    'source_sha256' => $fixture['source_sha256'],
    'suggestion_count' => $fixture['suggestion_count'],
    'revision_id' => $fixture['revision_id'],
    'image_sha256' => $fixture['image_sha256'],
  ]);
}

function step16_inspect(): void {
  $provider_manager = \Drupal::service('ai.provider');
  $provider = $provider_manager->createInstance('openai');
  $function_manager = \Drupal::service('plugin.manager.ai.function_calls');
  $definitions = $function_manager->getDefinitions();
  $tool_probe_id = 'ai_agent:html_to_markdown';
  $required_modules = ['ai', 'ai_agents', 'ai_provider_openai', 'key', 'jsonapi', 'basic_auth'];
  $enabled_modules = array_values(array_intersect(
    $required_modules,
    array_keys(\Drupal::moduleHandler()->getModuleList()),
  ));
  $missing_modules = array_values(array_diff($required_modules, $enabled_modules));
  if ($missing_modules !== []) {
    step16_fail('Required modules are not enabled: ' . implode(', ', $missing_modules));
  }
  if (!method_exists(ChatInput::class, 'setChatStructuredJsonSchema')) {
    step16_fail('Pinned Drupal AI ChatInput lacks setChatStructuredJsonSchema().');
  }
  if (!method_exists(ChatInput::class, 'setChatTools')) {
    step16_fail('Pinned Drupal AI ChatInput lacks setChatTools().');
  }
  if (!array_key_exists($tool_probe_id, $definitions)) {
    step16_fail('The required harmless FunctionCall probe ai_agent:html_to_markdown is unavailable.');
  }
  $tool_probe = $function_manager->createInstance($tool_probe_id);
  $normalized_probe = $tool_probe->normalize();
  if ($normalized_probe === NULL || $normalized_probe === [] || $normalized_probe === '') {
    step16_fail('The harmless FunctionCall probe could not be normalized.');
  }

  step16_emit([
    'test_id' => 'INSPECT-DR-001',
    'status' => 'pass',
    'provider_class' => get_class($provider),
    'chat_input_class' => ChatInput::class,
    'chat_message_class' => ChatMessage::class,
    'image_file_class' => ImageFile::class,
    'supports_structured_schema_method' => method_exists(ChatInput::class, 'setChatStructuredJsonSchema'),
    'supports_tool_input_method' => method_exists(ChatInput::class, 'setChatTools'),
    'tool_probe_plugin_id' => $tool_probe_id,
    'tool_probe_normalized' => step16_object_summary($normalized_probe),
    'enabled_modules' => $enabled_modules,
  ]);
}

/**
 * @return array<string, mixed>
 */
function step16_schema(): array {
  return [
    'type' => 'object',
    'additionalProperties' => FALSE,
    'required' => ['image_purpose', 'proposed_alt_text', 'context_alignment'],
    'properties' => [
      'image_purpose' => ['type' => 'string', 'minLength' => 1, 'maxLength' => 500],
      'proposed_alt_text' => ['type' => 'string', 'minLength' => 1, 'maxLength' => 250],
      'context_alignment' => ['type' => 'string', 'minLength' => 1, 'maxLength' => 500],
    ],
  ];
}

/**
 * @return array<string, string>
 */
function step16_validate_model_output(string $text): array {
  $trimmed = trim($text);
  if (str_starts_with($trimmed, '```')) {
    $trimmed = preg_replace('/^```(?:json)?\s*|\s*```$/i', '', $trimmed) ?? $trimmed;
  }
  $decoded = json_decode($trimmed, TRUE);
  if (!is_array($decoded)) {
    step16_fail('Drupal AI structured response was not a JSON object: ' . substr($trimmed, 0, 500));
  }
  $required = ['image_purpose', 'proposed_alt_text', 'context_alignment'];
  $actual_keys = array_keys($decoded);
  sort($actual_keys);
  $expected_keys = $required;
  sort($expected_keys);
  if ($actual_keys !== $expected_keys) {
    step16_fail('Drupal AI structured response must contain exactly the three Step 16 properties.');
  }
  foreach ($required as $key) {
    if (!isset($decoded[$key]) || !is_string($decoded[$key]) || trim($decoded[$key]) === '') {
      step16_fail('Drupal AI structured response is missing nonempty ' . $key . '.');
    }
  }
  if (mb_strlen($decoded['proposed_alt_text']) > 250) {
    step16_fail('Drupal AI proposed_alt_text exceeds 250 characters.');
  }
  return array_intersect_key($decoded, array_flip($required));
}

function step16_provider(string $model_id): object {
  if ($model_id === '') {
    step16_fail('A candidate model ID is required.');
  }
  $provider = \Drupal::service('ai.provider')->createInstance('openai');
  if (method_exists($provider, 'setConfiguration')) {
    $provider->setConfiguration(['temperature' => 0.0]);
  }
  return $provider;
}

function step16_vision(string $runtime_dir, string $model_id): void {
  $fixture_path = rtrim($runtime_dir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'fixture.json';
  $image_path = rtrim($runtime_dir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'fixture.png';
  if (!is_file($fixture_path) || !is_file($image_path)) {
    step16_fail('Run fixture extraction before the Drupal vision check.');
  }
  $fixture = json_decode((string) file_get_contents($fixture_path), TRUE);
  if (!is_array($fixture)) {
    step16_fail('Runtime fixture.json is invalid.');
  }
  $bytes = file_get_contents($image_path);
  if (!is_string($bytes) || hash('sha256', $bytes) !== ($fixture['image_sha256'] ?? NULL)) {
    step16_fail('Runtime fixture image does not match fixture metadata.');
  }

  $system = 'You are performing a bounded capability check for an accessibility workflow. Use only the supplied synthetic image and page context. Return only the requested structured object.';
  $prompt = sprintf(
    "PAGE CONTEXT\nTitle: %s\nBody: %s\n\nIMAGE METADATA\nFilename: %s\nMIME type: %s\nDimensions: %d x %d\n\nTASK\nInspect the attached image with the page context. Return image_purpose, proposed_alt_text, and context_alignment. Keep proposed_alt_text at 250 characters or fewer, do not repeat the filename, and return no extra properties.",
    $fixture['article_title'],
    $fixture['article_body_plain'],
    $fixture['filename'],
    $fixture['mime_type'],
    $fixture['width'],
    $fixture['height'],
  );
  $message = new ChatMessage('user', $prompt);
  $message->setFile(new ImageFile($bytes, (string) $fixture['mime_type'], (string) $fixture['filename']));
  $input = new ChatInput([$message]);
  if (method_exists($input, 'setSystemPrompt')) {
    $input->setSystemPrompt($system);
  }
  $input->setChatStructuredJsonSchema([
    'name' => 'vision_spike_output',
    'description' => 'Structured result for the Step 16 synthetic vision capability check.',
    'strict' => TRUE,
    'schema' => step16_schema(),
  ]);
  $provider = step16_provider($model_id);
  if (!method_exists($input, 'setSystemPrompt') && method_exists($provider, 'setChatSystemRole')) {
    $provider->setChatSystemRole($system);
  }
  $response = $provider->chat($input, $model_id, ['phase0-step16', 'vision']);
  $message_out = $response->getNormalized();
  $output = step16_validate_model_output((string) $message_out->getText());

  step16_emit([
    'test_id' => 'VISION-DR-001',
    'status' => 'pass',
    'framework' => 'drupal_ai',
    'model_id' => $model_id,
    'temperature' => 0.0,
    'image_representation' => 'ImageFile(binary PNG) normalized by Drupal AI/OpenAI provider to provider-native image input',
    'comparison_representation' => 'base64_data_url',
    'image_detail' => 'auto/provider default',
    'image_byte_length' => strlen($bytes),
    'image_sha256' => hash('sha256', $bytes),
    'context_sha256' => $fixture['context_sha256'],
    'structured_output_mechanism' => 'ChatInput::setChatStructuredJsonSchema(strict=true)',
    'output' => $output,
    'base64_retained' => FALSE,
  ]);
}

/**
 * @return array<string, mixed>
 */
function step16_object_summary(mixed $value, int $depth = 0): array {
  if ($depth > 3) {
    return ['type' => get_debug_type($value)];
  }
  if (is_array($value)) {
    $result = [];
    foreach ($value as $key => $item) {
      $result[(string) $key] = is_scalar($item) || $item === NULL
        ? $item
        : step16_object_summary($item, $depth + 1);
    }
    return $result;
  }
  if (is_object($value)) {
    $result = ['class' => get_class($value)];
    foreach (['getName', 'getPluginId', 'getText', 'getArguments', 'getFunctionName', 'getFunctions', 'getTools'] as $method) {
      if (method_exists($value, $method)) {
        try {
          $method_value = $value->{$method}();
          $result[$method] = is_scalar($method_value) || $method_value === NULL
            ? $method_value
            : step16_object_summary($method_value, $depth + 1);
        }
        catch (Throwable) {
          $result[$method] = '<unavailable>';
        }
      }
    }
    return $result;
  }
  return ['type' => get_debug_type($value), 'value' => is_scalar($value) ? $value : NULL];
}

function step16_tool(string $model_id): void {
  $manager = \Drupal::service('plugin.manager.ai.function_calls');
  $definitions = $manager->getDefinitions();
  $tool_probe_id = 'ai_agent:html_to_markdown';
  if (!array_key_exists($tool_probe_id, $definitions)) {
    step16_fail('The required harmless FunctionCall probe ai_agent:html_to_markdown is unavailable.');
  }
  $function = $manager->createInstance($tool_probe_id);
  $input = new ChatInput([
    new ChatMessage('user', 'Use the HTML to Markdown tool exactly once to convert this exact HTML: <p><strong>Step 16</strong> tool probe.</p> Do not answer without the tool.'),
  ]);
  $input->setChatTools(new ToolsInput([$function->normalize()]));
  $provider = step16_provider($model_id);
  $response = $provider->chat($input, $model_id, ['phase0-step16', 'tool']);
  $normalized = $response->getNormalized();
  $text = method_exists($normalized, 'getText') ? (string) $normalized->getText() : '';
  $tools = method_exists($normalized, 'getTools') ? $normalized->getTools() : NULL;
  if ($tools === NULL || $tools === [] || (is_countable($tools) && count($tools) === 0)) {
    step16_fail('The Drupal AI normalized response did not contain a tool call.');
  }
  $summary = step16_object_summary($tools);
  $serialized = json_encode($summary, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) ?: '';
  $serialized_lower = strtolower($serialized);
  $detected = str_contains($serialized_lower, 'html_to_markdown')
    || str_contains($serialized_lower, 'html to markdown')
    || str_contains($serialized_lower, 'step 16')
    || str_contains($serialized_lower, '<strong>');
  if (!$detected) {
    step16_fail('The Drupal AI normalized tool payload did not identify the HTML-to-Markdown probe.');
  }
  step16_emit([
    'test_id' => 'TOOL-DR-001',
    'status' => 'pass',
    'framework' => 'drupal_ai',
    'model_id' => $model_id,
    'temperature' => 0.0,
    'tool_plugin_id' => $tool_probe_id,
    'tool_call_detected' => TRUE,
    'tool_payload_present' => TRUE,
    'tool_expected_operation' => 'Convert deterministic synthetic HTML to Markdown; plugin execution is not performed by this capability check.',
    'tool_mechanism' => 'ChatInput::setChatTools(ToolsInput) with Drupal FunctionCall plugin',
    'normalized_text_characters' => mb_strlen($text),
    'tool_summary' => $summary,
  ]);
}
