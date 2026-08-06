<?php

declare(strict_types=1);

use Drupal\Core\Session\AccountInterface;
use Drupal\Core\Session\AnonymousUserSession;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

/**
 * Direct model-free Step 1.03 adapter exercise.
 *
 * Raw image representation is emitted only to the runner's in-memory capture
 * pipe. The capture validates and sanitizes it before writing evidence.
 *
 * Usage from drupal/:
 *   ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot
 *   ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- exercise
 */

const GATE1_STEP03_TARGET_SHA256 = '1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728';
const GATE1_STEP03_ARTICLE_SOURCE_SHA256 = 'f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17';
const GATE1_STEP03_RUN_ID = 'drupal_ai-20260806T030000Z-step03';

/** @var array<int, mixed> $extra */
$mode = is_array($extra ?? NULL) ? (string) ($extra[0] ?? '') : '';
$GLOBALS['gate1_step03_stage'] = 'bootstrap';

function gate1_step03_emit(array $value): void {
  print json_encode(
    $value,
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ) . PHP_EOL;
}

function gate1_step03_sort(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate1_step03_sort', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate1_step03_sort($item);
  }
  return $value;
}

function gate1_step03_hash(mixed $value): string {
  return hash('sha256', gate1_step03_encode($value));
}

function gate1_step03_encode(mixed $value): string {
  return json_encode(
    gate1_step03_sort($value),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );
}

function gate1_step03_user(string $name): UserInterface {
  $matches = \Drupal::entityTypeManager()->getStorage('user')->loadByProperties(['name' => $name]);
  $account = reset($matches);
  if (!$account instanceof UserInterface) {
    throw new RuntimeException('Required test account is unavailable: ' . $name);
  }
  return $account;
}

function gate1_step03_as(AccountInterface $account, callable $callback): mixed {
  $switcher = \Drupal::service('account_switcher');
  $switcher->switchTo($account);
  try {
    return $callback();
  }
  finally {
    $switcher->switchBack();
  }
}

/**
 * @param array<string, mixed> $inputs
 *   Context values keyed by the exact input name.
 *
 * @return array<string, mixed>
 *   Structured tool-result envelope.
 */
function gate1_step03_call(string $plugin_id, array $inputs, string $call_id): array {
  $manager = \Drupal::service('plugin.manager.ai.function_calls');
  $plugin = $manager->createInstance($plugin_id);
  $plugin->setToolsId($call_id);
  foreach ($inputs as $name => $value) {
    $plugin->setContextValue($name, $value);
  }
  $plugin->execute();
  $structured = $plugin->getStructuredOutput();
  $readable = json_decode($plugin->getReadableOutput(), TRUE, 512, JSON_THROW_ON_ERROR);
  if ($structured !== $readable) {
    throw new RuntimeException('Readable and structured adapter output diverged.');
  }
  return $structured;
}

/**
 * @return array<string, mixed>
 *   Source-only snapshot facts.
 */
function gate1_step03_state(): array {
  $container = \Drupal::getContainer();
  $storage = $container->get('entity_type.manager')->getStorage('node');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->sort('nid', 'ASC')
    ->execute();
  $predecessor_articles = [];
  $gate05_certification_articles = [];
  $step03_extended_articles = [];
  $safe_records = [];
  foreach ($storage->loadMultiple($ids) as $node) {
    if (!$node instanceof NodeInterface) {
      continue;
    }
    $predecessor_images = [];
    $extended_images = [];
    foreach ($node->get('field_image') as $delta => $item) {
      $file = $item->entity;
      $predecessor_image = [
        'delta' => (int) $delta,
        'file_uuid' => $file instanceof FileInterface ? $file->uuid() : NULL,
        'alt' => (string) ($item->alt ?? ''),
        'title' => (string) ($item->title ?? ''),
      ];
      $predecessor_images[] = $predecessor_image;
      $extended_images[] = [
        'delta' => $predecessor_image['delta'],
        'target_id' => (int) ($item->target_id ?? 0),
        'file_uuid' => $predecessor_image['file_uuid'],
        'alt' => $predecessor_image['alt'],
        'title' => $predecessor_image['title'],
      ];
    }

    $predecessor_article = [
      'node_uuid' => $node->uuid(),
      'revision_id' => (int) $node->getRevisionId(),
      'title' => (string) $node->label(),
      'status' => (bool) $node->isPublished(),
      'images' => $predecessor_images,
    ];
    $body = [
      'value' => '',
      'summary' => '',
      'format' => NULL,
    ];
    if ($node->hasField('body') && !$node->get('body')->isEmpty()) {
      $body_item = $node->get('body')->first();
      $body = [
        'value' => (string) ($body_item?->value ?? ''),
        'summary' => (string) ($body_item?->summary ?? ''),
        'format' => $body_item?->format,
      ];
    }
    $gate05_article = $predecessor_article;
    $gate05_article['body'] = $body;
    $extended_article = [
      'nid' => (int) $node->id(),
      'uuid' => $node->uuid(),
      'revision_id' => (int) $node->getRevisionId(),
      'title' => (string) $node->label(),
      'body' => (string) ($node->get('body')->value ?? ''),
      'images' => $extended_images,
    ];
    $predecessor_articles[] = $predecessor_article;
    $gate05_certification_articles[] = $gate05_article;
    $step03_extended_articles[] = $extended_article;
    $safe_records[] = [
      'position' => count($predecessor_articles),
      'node_uuid_sha256' => hash('sha256', $node->uuid()),
      'revision_id' => (int) $node->getRevisionId(),
      'image_count' => count($predecessor_images),
      'predecessor_record_sha256' => gate1_step03_hash($predecessor_article),
      'gate05_certification_record_sha256' => gate1_step03_hash($gate05_article),
      'step03_extended_record_sha256' => gate1_step03_hash($extended_article),
    ];
  }
  $predecessor_json = gate1_step03_encode($predecessor_articles);
  $gate05_json = gate1_step03_encode($gate05_certification_articles);
  $step03_extended_json = gate1_step03_encode($step03_extended_articles);
  $predecessor_hash = hash('sha256', $predecessor_json);
  $suggestion_count = (int) $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'alt_text_suggestion')
    ->count()
    ->execute();
  $agent_bot = gate1_step03_user('agent_bot');
  $targets = gate1_step03_as(
    $agent_bot,
    static fn(): array => $container->get('agentic_harness_tools.image_review_finder')->find(),
  );
  $target_hash = gate1_step03_hash($targets);
  return [
    'status' => 'pass',
    'article_count' => count($predecessor_articles),
    'suggestion_count' => $suggestion_count,
    'target_count' => count($targets),
    'target_sequence_sha256' => $target_hash,
    'canonical_target_sequence' => $targets[0]['sequence'] ?? NULL,
    'canonical_target_identity_sha256' => isset($targets[0]) ? gate1_step03_hash($targets[0]) : NULL,
    'article_source_sha256' => $predecessor_hash,
    'step03_extended_article_source_sha256' => hash('sha256', $step03_extended_json),
    'gate05_certification_article_source_sha256' => hash('sha256', $gate05_json),
    'article_source_hash_reconciliation' => [
      'classification' => 'hash_definition_drift_only',
      'actual_source_drift' => FALSE,
      'record_order' => 'node query sorted by nid ASC; image values preserve field delta order',
      'canonicalization' => 'recursively ksort associative arrays; preserve list order',
      'json_encoding_flags' => ['JSON_UNESCAPED_SLASHES', 'JSON_UNESCAPED_UNICODE', 'JSON_THROW_ON_ERROR'],
      'predecessor_step02' => [
        'source' => 'drupal/scripts/gate1-step02-runtime-probe.php::gate1_step02_snapshot/gate1_step02_sort/gate1_step02_sha256',
        'entities' => 'all article nodes',
        'article_properties' => ['node_uuid', 'revision_id', 'title', 'status', 'images'],
        'image_properties' => ['delta', 'file_uuid', 'alt', 'title'],
        'node_id_included' => FALSE,
        'node_uuid_included' => TRUE,
        'revision_id_included' => TRUE,
        'image_or_file_metadata' => 'field delta and file UUID; no numeric file ID, URI, MIME, dimensions, or bytes',
        'null_empty_treatment' => 'missing file entity -> null file_uuid; missing alt/title -> empty string',
        'canonical_payload_bytes' => strlen($predecessor_json),
        'sha256' => $predecessor_hash,
      ],
      'gate05_step03_projection' => [
        'source' => 'drupal/scripts/gate05-step03.php snapshot mode/gate05_step03_canonicalize',
        'entities' => 'all article nodes',
        'article_properties' => ['node_uuid', 'revision_id', 'title', 'status', 'images'],
        'image_properties' => ['delta', 'file_uuid', 'alt', 'title'],
        'node_id_included' => FALSE,
        'node_uuid_included' => TRUE,
        'revision_id_included' => TRUE,
        'image_or_file_metadata' => 'field delta and file UUID; no numeric file ID, URI, MIME, dimensions, or bytes',
        'null_empty_treatment' => 'missing file entity -> null file_uuid; missing alt/title -> empty string',
        'canonical_payload_bytes' => strlen($predecessor_json),
        'sha256' => $predecessor_hash,
      ],
      'gate05_certification' => [
        'source' => 'drupal/scripts/gate05-step04.php::gate05_step04_snapshot/gate05_step04_canonicalize',
        'entities' => 'all article nodes',
        'article_properties' => ['node_uuid', 'revision_id', 'title', 'status', 'body', 'images'],
        'body_properties' => ['value', 'summary', 'format'],
        'image_properties' => ['delta', 'file_uuid', 'alt', 'title'],
        'node_id_included' => FALSE,
        'node_uuid_included' => TRUE,
        'revision_id_included' => TRUE,
        'image_or_file_metadata' => 'field delta and file UUID; no numeric file ID, URI, MIME, dimensions, or bytes',
        'null_empty_treatment' => 'empty body -> empty value/summary and null format; missing file -> null UUID; missing alt/title -> empty string',
        'canonical_payload_bytes' => strlen($gate05_json),
        'sha256' => hash('sha256', $gate05_json),
      ],
      'original_step03_extended' => [
        'source' => 'drupal/scripts/gate1-step03-adapter-exercise.php::gate1_step03_state/gate1_step03_sort/gate1_step03_hash (original projection retained under a distinct diagnostic name)',
        'entities' => 'all article nodes',
        'article_properties' => ['nid', 'uuid', 'revision_id', 'title', 'body', 'images'],
        'image_properties' => ['delta', 'target_id', 'file_uuid', 'alt', 'title'],
        'node_id_included' => TRUE,
        'node_uuid_included' => TRUE,
        'revision_id_included' => TRUE,
        'image_or_file_metadata' => 'numeric file target ID, field delta, and file UUID; no URI, MIME, dimensions, or bytes',
        'null_empty_treatment' => 'missing body/alt/title -> empty string; missing target_id -> 0; missing file -> null UUID',
        'canonical_payload_bytes' => strlen($step03_extended_json),
        'sha256' => hash('sha256', $step03_extended_json),
      ],
      'structural_differences' => [
        'original Step 1.03 added nid, scalar body value, and image target_id',
        'original Step 1.03 renamed node_uuid to uuid',
        'original Step 1.03 omitted status',
        'Gate 0.5 certification additionally includes structured body value, summary, and format',
      ],
      'safe_record_facts' => $safe_records,
    ],
    'seeded_clean' => count($predecessor_articles) === 20
      && $suggestion_count === 0
      && count($targets) === 12
      && ($targets[0]['sequence'] ?? NULL) === 1
      && $target_hash === GATE1_STEP03_TARGET_SHA256
      && $predecessor_hash === GATE1_STEP03_ARTICLE_SOURCE_SHA256,
    'module_enabled' => $container->get('module_handler')->moduleExists('agentic_harness_drupal_ai'),
    'model_call_performed' => FALSE,
    'network_call_performed' => FALSE,
    'raw_image_retained' => FALSE,
    'secret_retained' => FALSE,
  ];
}

/**
 * @return array<string, mixed>
 *   Complete raw exercise result for in-memory validation and sanitization.
 */
function gate1_step03_exercise(): array {
  $gate1_step03_stage = &$GLOBALS['gate1_step03_stage'];

  $gate1_step03_stage = 'module-check';
  $container = \Drupal::getContainer();
  if (!$container->get('module_handler')->moduleExists('agentic_harness_drupal_ai')) {
    throw new RuntimeException('Step 1.03 module is not enabled for the temporary exercise.');
  }

  $gate1_step03_stage = 'event-listeners';
  $provider_events = 0;
  $agent_events = 0;
  $dispatcher = $container->get('event_dispatcher');
  $dispatcher->addListener(
    \Drupal\ai\Event\PreGenerateResponseEvent::EVENT_NAME,
    static function () use (&$provider_events): void {
      $provider_events++;
    },
  );
  $dispatcher->addListener(
    \Drupal\ai_agents\Event\AgentRequestEvent::EVENT_NAME,
    static function () use (&$agent_events): void {
      $agent_events++;
    },
  );

  $gate1_step03_stage = 'account-load';
  $agent_bot = gate1_step03_user('agent_bot');
  $editor = gate1_step03_user('editor_dana');
  $anonymous = new AnonymousUserSession();
  $manager = $container->get('plugin.manager.ai.function_calls');
  $expected_classes = [
    'discover_targets' => Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall\DiscoverTargets::class,
    'get_image_context' => Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall\GetImageContext::class,
    'submit_recommendation' => Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall\SubmitRecommendation::class,
    'get_recommendation_status' => Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall\GetRecommendationStatus::class,
  ];
  $gate1_step03_stage = 'plugin-discovery';
  $definitions = $manager->getDefinitions();
  $discovery = [];
  $normalized_inputs = [];
  foreach ($expected_classes as $plugin_id => $expected_class) {
    if (($definitions[$plugin_id]['class'] ?? NULL) !== $expected_class) {
      throw new RuntimeException('FunctionCall definition class mismatch: ' . $plugin_id);
    }
    $instance = $manager->createInstance($plugin_id);
    $discovery[$plugin_id] = [
      'definition_class' => $definitions[$plugin_id]['class'],
      'instance_class' => $instance::class,
      'function_name' => $definitions[$plugin_id]['function_name'],
      'group' => $definitions[$plugin_id]['group'],
    ];
    $gate1_step03_stage = 'plugin-normalization-' . $plugin_id;
    $normalized_inputs[$plugin_id] = $instance->normalize()->renderFunctionArray()['parameters'];
  }

  $gate1_step03_stage = 'discover-targets';
  $discover = gate1_step03_as(
    $agent_bot,
    static fn(): array => gate1_step03_call('discover_targets', [], 'step03-discover'),
  );
  $target = $discover['data']['targets'][0] ?? NULL;
  if (!is_array($target)) {
    throw new RuntimeException('Canonical target was not returned by discovery.');
  }
  $gate1_step03_stage = 'get-image-context';
  $context = gate1_step03_as(
    $agent_bot,
    static fn(): array => gate1_step03_call('get_image_context', ['target' => $target], 'step03-context'),
  );
  $recommendation = [
    'schema_version' => 1,
    'target' => $target,
    'proposed_alt_text' => 'Red and blue geometric shapes arranged on a pale background.',
    'source_framework' => 'drupal_ai',
    'run_id' => GATE1_STEP03_RUN_ID,
    'evidence_hash' => $context['data']['evidence_hash'],
    'validator_version' => 'gate05-validator-1.0.0',
  ];

  $gate1_step03_stage = 'permission-controls';
  $permission_inputs = [
    'discover_targets' => [],
    'get_image_context' => ['target' => $target],
    'submit_recommendation' => ['recommendation' => $recommendation],
    'get_recommendation_status' => ['recommendation_id' => '1'],
  ];
  $permission_denials = [];
  foreach (['anonymous' => $anonymous, 'editor_dana' => $editor] as $account_name => $account) {
    foreach ($permission_inputs as $plugin_id => $inputs) {
      $permission_denials[$account_name][$plugin_id] = gate1_step03_as(
        $account,
        static fn(): array => gate1_step03_call(
          $plugin_id,
          $inputs,
          'step03-denial-' . $account_name . '-' . $plugin_id,
        ),
      );
    }
  }

  $malformed_target = $target;
  unset($malformed_target['node_uuid']);
  $stale_target = $target;
  $stale_target['revision_id']++;
  $unexpected_target = $target;
  $unexpected_target['unexpected'] = 'rejected';
  $malformed_recommendation = $recommendation;
  unset($malformed_recommendation['proposed_alt_text']);
  $unexpected_recommendation = $recommendation;
  $unexpected_recommendation['unexpected'] = 'rejected';

  $gate1_step03_stage = 'negative-controls';
  $negative_controls = gate1_step03_as($agent_bot, static function () use (
    $malformed_target,
    $stale_target,
    $unexpected_target,
    $malformed_recommendation,
    $unexpected_recommendation,
  ): array {
    return [
      'malformed_target' => gate1_step03_call('get_image_context', ['target' => $malformed_target], 'step03-negative-malformed-target'),
      'stale_target_identity' => gate1_step03_call('get_image_context', ['target' => $stale_target], 'step03-negative-stale-target'),
      'unexpected_target_property' => gate1_step03_call('get_image_context', ['target' => $unexpected_target], 'step03-negative-unexpected-target'),
      'malformed_recommendation' => gate1_step03_call('submit_recommendation', ['recommendation' => $malformed_recommendation], 'step03-negative-malformed-recommendation'),
      'unexpected_recommendation_property' => gate1_step03_call('submit_recommendation', ['recommendation' => $unexpected_recommendation], 'step03-negative-unexpected-recommendation'),
      'invalid_status_identifier' => gate1_step03_call('get_recommendation_status', ['recommendation_id' => '0-not-valid'], 'step03-negative-invalid-status'),
    ];
  });

  $gate1_step03_stage = 'before-submission-state';
  $state_before_submission = gate1_step03_state();
  $gate1_step03_stage = 'submit-recommendation';
  $submission = gate1_step03_as(
    $agent_bot,
    static fn(): array => gate1_step03_call('submit_recommendation', ['recommendation' => $recommendation], 'step03-submit'),
  );
  $gate1_step03_stage = 'submit-recommendation-replay';
  $replay = gate1_step03_as(
    $agent_bot,
    static fn(): array => gate1_step03_call('submit_recommendation', ['recommendation' => $recommendation], 'step03-submit-replay'),
  );
  $gate1_step03_stage = 'get-recommendation-status';
  $status = gate1_step03_as(
    $agent_bot,
    static fn(): array => gate1_step03_call(
      'get_recommendation_status',
      ['recommendation_id' => (string) $submission['data']['node_id']],
      'step03-status',
    ),
  );
  $gate1_step03_stage = 'after-submission-state';
  $state_after_submission = gate1_step03_state();

  $gate1_step03_stage = 'unknown-exception';
  $unknown_marker = 'DO_NOT_EXPOSE_UNKNOWN_EXCEPTION_DETAIL';
  $unknown = $container->get('agentic_harness_drupal_ai.tool_result_runner')->run(
    'get_image_context',
    'step03-unknown-exception',
    static fn(): array => throw new RuntimeException($unknown_marker),
  );

  $gate1_step03_stage = 'assemble-output';
  return [
    'schema_version' => 1,
    'status' => 'pass',
    'plugin_manager' => $manager::class,
    'discovery' => $discovery,
    'normalized_inputs' => $normalized_inputs,
    'delegation_services' => [
      'discover_targets' => $container->get('agentic_harness_tools.image_review_finder')::class,
      'get_image_context' => $container->get('agentic_harness_tools.image_context_provider')::class,
      'submit_recommendation' => $container->get('agentic_harness_tools.recommendation_submitter')::class,
      'get_recommendation_status' => $container->get('agentic_harness_tools.recommendation_status_provider')::class,
    ],
    'accounts' => [
      'success_account' => 'agent_bot',
      'denied_accounts' => ['anonymous', 'editor_dana'],
      'administrative_account_substituted' => FALSE,
    ],
    'operations' => [
      'discover_targets' => $discover,
      'get_image_context' => $context,
      'submit_recommendation' => $submission,
      'submit_recommendation_replay' => $replay,
      'get_recommendation_status' => $status,
    ],
    'fixture_recommendation' => $recommendation,
    'permission_denials' => $permission_denials,
    'negative_controls' => $negative_controls,
    'unknown_exception' => [
      'envelope' => $unknown,
      'marker' => $unknown_marker,
      'marker_exposed' => str_contains(json_encode($unknown, JSON_THROW_ON_ERROR), $unknown_marker),
    ],
    'state_before_submission' => $state_before_submission,
    'state_after_submission' => $state_after_submission,
    'provider_pre_request_events_observed' => $provider_events,
    'agent_request_events_observed' => $agent_events,
    'model_call_performed' => FALSE,
    'network_call_performed' => FALSE,
    'api_credit_used' => FALSE,
    'runtime_state_storage_opened' => FALSE,
    'ai_agent_configuration_created' => FALSE,
  ];
}

try {
  match ($mode) {
    'snapshot' => gate1_step03_emit(gate1_step03_state()),
    'exercise' => gate1_step03_emit(gate1_step03_exercise()),
    default => throw new InvalidArgumentException('Usage: snapshot|exercise'),
  };
}
catch (Throwable $exception) {
  $safe_stage = preg_replace('/[^A-Za-z0-9_.:-]/', '', (string) $GLOBALS['gate1_step03_stage']);
  fwrite(
    STDERR,
    sprintf(
      '[ERROR] Step 1.03 direct exercise failed safely at %s (%s).%s',
      $safe_stage,
      $exception::class,
      PHP_EOL,
    ),
  );
  exit(1);
}
