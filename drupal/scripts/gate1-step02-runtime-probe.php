<?php

declare(strict_types=1);

use Drupal\ai\Dto\StructuredOutputSchema;
use Drupal\ai\Event\PreGenerateResponseEvent;
use Drupal\ai\OperationType\Chat\ChatInput;
use Drupal\ai_agents\Event\AgentRequestEvent;
use Drupal\ai_agents\Task\Task;
use Drupal\Component\Serialization\Yaml;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;

/**
 * Non-networked, non-mutating Gate 1 Step 1.02 Drupal runtime probe.
 *
 * Usage from drupal/:
 *   ddev drush --quiet php:script scripts/gate1-step02-runtime-probe.php -- snapshot
 *   ddev drush --quiet php:script scripts/gate1-step02-runtime-probe.php -- runtime
 */

const GATE1_STEP02_PROBE_VERSION = '1.0.0';
const GATE1_STEP02_TARGET_SHA256 = '1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728';
const GATE1_STEP02_MODEL = 'gpt-4.1-mini-2025-04-14';

/** @var array<int, mixed> $extra */
$mode = is_array($extra ?? NULL) ? (string) ($extra[0] ?? '') : '';

function gate1_step02_emit(array $value): void {
  print json_encode(
    $value,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ) . PHP_EOL;
}

function gate1_step02_sort(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate1_step02_sort', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate1_step02_sort($item);
  }
  return $value;
}

function gate1_step02_sha256(mixed $value): string {
  return hash('sha256', json_encode(
    gate1_step02_sort($value),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ));
}

function gate1_step02_method_signature(string $class, string $method): array {
  $reflection = new ReflectionMethod($class, $method);
  $parameters = [];
  $rendered = [];
  foreach ($reflection->getParameters() as $parameter) {
    $type = $parameter->hasType() ? (string) $parameter->getType() : NULL;
    $piece = ($type !== NULL ? $type . ' ' : '')
      . ($parameter->isPassedByReference() ? '&' : '')
      . ($parameter->isVariadic() ? '...' : '')
      . '$' . $parameter->getName();
    if ($parameter->isDefaultValueAvailable()) {
      $piece .= ' = ' . ($parameter->isDefaultValueConstant()
        ? $parameter->getDefaultValueConstantName()
        : var_export($parameter->getDefaultValue(), TRUE));
    }
    $rendered[] = $piece;
    $parameters[] = [
      'name' => $parameter->getName(),
      'type' => $type,
      'allows_null' => $parameter->allowsNull(),
      'by_reference' => $parameter->isPassedByReference(),
      'variadic' => $parameter->isVariadic(),
      'optional' => $parameter->isOptional(),
      'has_default' => $parameter->isDefaultValueAvailable(),
    ];
  }
  $return_type = $reflection->hasReturnType() ? (string) $reflection->getReturnType() : NULL;
  $signature = $reflection->getName() . '(' . implode(', ', $rendered) . ')'
    . ($return_type !== NULL ? ': ' . $return_type : '');
  return [
    'declaring_class' => $reflection->getDeclaringClass()->getName(),
    'visibility' => $reflection->isPublic() ? 'public' : ($reflection->isProtected() ? 'protected' : 'private'),
    'static' => $reflection->isStatic(),
    'signature' => $signature,
    'parameters' => $parameters,
    'return_type_declared' => $return_type !== NULL,
    'return_type' => $return_type,
  ];
}

function gate1_step02_reflection_surface(array $targets): array {
  $surface = [];
  foreach ($targets as $class => $methods) {
    $reflection = new ReflectionClass($class);
    $public_methods = array_map(
      static fn(ReflectionMethod $method): string => $method->getName(),
      $reflection->getMethods(ReflectionMethod::IS_PUBLIC),
    );
    sort($public_methods);
    $signatures = [];
    foreach ($methods as $method) {
      $signatures[$method] = gate1_step02_method_signature($class, $method);
    }
    $surface[$class] = [
      'constructor' => $reflection->hasMethod('__construct')
        ? gate1_step02_method_signature($class, '__construct')
        : NULL,
      'public_method_names' => array_values(array_unique($public_methods)),
      'relevant_method_signatures' => $signatures,
    ];
  }
  return $surface;
}

function gate1_step02_service_definition(string $path, string $service_id): array {
  $decoded = Yaml::decode((string) file_get_contents($path));
  $definition = $decoded['services'][$service_id] ?? NULL;
  if (!is_array($definition)) {
    throw new RuntimeException('Missing installed service definition: ' . $service_id);
  }
  return [
    'class' => $definition['class'] ?? NULL,
    'parent' => $definition['parent'] ?? NULL,
    'arguments' => array_values($definition['arguments'] ?? []),
    'factory' => $definition['factory'] ?? NULL,
  ];
}

function gate1_step02_relative_source(string $path): string {
  $root = dirname(DRUPAL_ROOT);
  return str_starts_with($path, $root . '/') ? substr($path, strlen($root) + 1) : $path;
}

function gate1_step02_composer_versions(): array {
  $lock_path = dirname(DRUPAL_ROOT) . '/composer.lock';
  $lock = json_decode((string) file_get_contents($lock_path), TRUE, 512, JSON_THROW_ON_ERROR);
  $wanted = [
    'drupal/core-recommended' => '11.4.4',
    'drupal/ai' => '1.4.5',
    'drupal/ai_agents' => '1.3.2',
    'drupal/ai_provider_openai' => '1.2.3',
  ];
  $actual = [];
  foreach ($lock['packages'] ?? [] as $package) {
    $name = $package['name'] ?? '';
    if (array_key_exists($name, $wanted)) {
      $actual[$name] = (string) ($package['version'] ?? '');
    }
  }
  ksort($actual);
  if ($actual !== $wanted) {
    ksort($wanted);
    if ($actual !== $wanted) {
      throw new RuntimeException('Pinned Composer versions do not match Step 1.02.');
    }
  }
  return $actual;
}

function gate1_step02_snapshot(): array {
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
    if ($node->hasField('field_image')) {
      foreach ($node->get('field_image') as $delta => $item) {
        $file = $item->entity;
        $images[] = [
          'delta' => (int) $delta,
          'file_uuid' => $file instanceof FileInterface ? $file->uuid() : NULL,
          'alt' => isset($item->alt) ? (string) $item->alt : '',
          'title' => isset($item->title) ? (string) $item->title : '',
        ];
      }
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

  $accounts = $container->get('entity_type.manager')->getStorage('user')->loadByProperties(['name' => 'agent_bot']);
  $agent_bot = reset($accounts);
  if (!$agent_bot instanceof \Drupal\user\UserInterface) {
    throw new RuntimeException('agent_bot was not found.');
  }
  $current_user = $container->get('current_user');
  $original_account = $current_user->getAccount();
  try {
    $current_user->setAccount($agent_bot);
    $targets = $container->get('agentic_harness_tools.image_review_finder')->find();
  }
  finally {
    $current_user->setAccount($original_account);
  }

  $target_sha = gate1_step02_sha256($targets);
  $seeded_clean = count($articles) === 20
    && $suggestion_count === 0
    && count($targets) === 12
    && ($targets[0]['sequence'] ?? NULL) === 1
    && $target_sha === GATE1_STEP02_TARGET_SHA256;
  if (!$seeded_clean) {
    throw new RuntimeException('Drupal does not match the frozen seeded-clean boundary.');
  }

  return [
    'schema_version' => 1,
    'probe_version' => GATE1_STEP02_PROBE_VERSION,
    'status' => 'pass',
    'article_count' => count($articles),
    'suggestion_count' => $suggestion_count,
    'target_count' => count($targets),
    'target_sequence_sha256' => $target_sha,
    'canonical_target_sequence' => (int) $targets[0]['sequence'],
    'canonical_target_identity_sha256' => gate1_step02_sha256($targets[0]),
    'article_source_sha256' => gate1_step02_sha256($articles),
    'seeded_clean' => TRUE,
    'model_call_performed' => FALSE,
    'raw_image_retained' => FALSE,
    'secret_retained' => FALSE,
  ];
}

function gate1_step02_runtime(): array {
  $container = \Drupal::getContainer();
  $dispatcher = $container->get('event_dispatcher');
  $provider_events = 0;
  $agent_request_events = 0;
  $dispatcher->addListener(PreGenerateResponseEvent::EVENT_NAME, static function () use (&$provider_events): void {
    $provider_events++;
  });
  $dispatcher->addListener(AgentRequestEvent::EVENT_NAME, static function () use (&$agent_request_events): void {
    $agent_request_events++;
  });

  $agent_manager = $container->get('plugin.manager.ai_agents');
  $definition_id = 'content_type_agent_triage';
  $definition = $agent_manager->getDefinition($definition_id);
  $agent = $agent_manager->createInstance($definition_id, $definition);
  $entity_type = $container->get('entity_type.manager')->getDefinition('ai_agent');

  $provider_manager = $container->get('ai.provider');
  $provider = $provider_manager->createInstance('openai');
  $provider->setConfiguration(['temperature' => 0.0]);
  $agent->setAiProvider($provider);
  $agent->setModelName(GATE1_STEP02_MODEL);
  $agent->setAiConfiguration(['temperature' => 0.0]);
  $agent->setTask(new Task('Non-networked runtime construction probe.'));
  $agent->overrideFunctions([
    'tools' => ['ai_agent:get_content_type_info' => TRUE],
    'tool_usage_limits' => [
      'ai_agent:get_content_type_info' => [
        'node_type' => [
          'action' => 'only_allow',
          'hide_property' => FALSE,
          'values' => ['article'],
        ],
      ],
    ],
    'tool_settings' => [
      'ai_agent:get_content_type_info' => [
        'require_usage' => TRUE,
        'return_directly' => FALSE,
      ],
    ],
  ]);
  $functions = $agent->getFunctions();
  $rendered_functions = [];
  foreach ($functions['normalized'] ?? [] as $name => $function) {
    $rendered_functions[$name] = $function->renderFunctionArray();
  }

  $strict_schema = new StructuredOutputSchema(
    name: 'drupal_ai_model_output',
    description: 'Raw Drupal AI model output.',
    strict: TRUE,
    json_schema: [
      'type' => 'object',
      'properties' => [
        'proposed_alt_text' => ['type' => 'string', 'minLength' => 1, 'maxLength' => 250],
      ],
      'required' => ['proposed_alt_text'],
      'additionalProperties' => FALSE,
    ],
  );
  $chat_input = new ChatInput([]);
  $chat_input->setChatStructuredJsonSchema($strict_schema);

  $openai_config = $container->get('config.factory')->get('ai_provider_openai.settings');
  $key_reference = (string) ($openai_config->get('api_key') ?? '');
  $temperature_definition = $provider->getAvailableConfiguration('chat', GATE1_STEP02_MODEL)['temperature'] ?? NULL;

  $keyvalue_factory = $container->get('keyvalue');
  $private_status = $container->get('ai_agents.private_temp_status_storage');
  $artifact_storage = $container->get('ai_agents.artifact_storage');

  $source_files = [
    'web/modules/contrib/ai/ai.services.yml',
    'web/modules/contrib/ai_agents/ai_agents.services.yml',
    'web/modules/contrib/ai_agents/src/PluginManager/AiAgentManager.php',
    'web/modules/contrib/ai_agents/src/PluginBase/AiAgentEntityWrapper.php',
    'web/modules/contrib/ai_agents/src/PluginInterfaces/AiAgentInterface.php',
    'web/modules/contrib/ai_agents/src/PluginInterfaces/ConfigAiAgentInterface.php',
    'web/modules/contrib/ai_agents/src/Entity/AiAgent.php',
    'web/modules/contrib/ai_agents/src/Task/Task.php',
    'web/modules/contrib/ai/src/AiProviderPluginManager.php',
    'web/modules/contrib/ai/src/Attribute/FunctionCall.php',
    'web/modules/contrib/ai/src/Base/FunctionCallBase.php',
    'web/modules/contrib/ai/src/Plugin/ProviderProxy.php',
    'web/modules/contrib/ai/src/OperationType/Chat/ChatInput.php',
    'web/modules/contrib/ai_provider_openai/src/Plugin/AiProvider/OpenAiProvider.php',
    'web/core/lib/Drupal/Core/KeyValueStore/KeyValueFactoryInterface.php',
    'web/core/lib/Drupal/Core/KeyValueStore/DatabaseStorage.php',
  ];
  $source_hashes = [];
  foreach ($source_files as $relative) {
    $path = dirname(DRUPAL_ROOT) . '/' . $relative;
    if (!is_file($path)) {
      throw new RuntimeException('Missing inspected source: ' . $relative);
    }
    $source_hashes[$relative] = hash_file('sha256', $path);
  }

  $interfaces = array_values(class_implements($agent));
  sort($interfaces);
  $serializable_keys = array_keys($agent->toArray());
  sort($serializable_keys);
  $methods = [
    'determineSolvability',
    'solve',
    'getChatHistory',
    'getToolResults',
    'toArray',
    'fromArray',
    'overrideFunctions',
  ];
  foreach ($methods as $method) {
    if (!method_exists($agent, $method)) {
      throw new RuntimeException('Required agent method is missing: ' . $method);
    }
  }
  $project_root = dirname(DRUPAL_ROOT);
  $reflection_surface = gate1_step02_reflection_surface([
    Drupal\ai_agents\PluginManager\AiAgentManager::class => ['__construct', 'createInstance', 'getDefinition'],
    Drupal\ai_agents\PluginBase\AiAgentEntityWrapper::class => [
      '__construct', 'setTask', 'setAiProvider', 'setModelName', 'setAiConfiguration',
      'overrideFunctions', 'getFunctions', 'determineSolvability', 'solve',
      'getChatHistory', 'getToolResults', 'getStructuredOutput', 'toArray', 'fromArray',
    ],
    Task::class => ['__construct', 'setDescription', 'setComments', 'setFiles'],
    Drupal\ai\AiProviderPluginManager::class => ['__construct', 'createInstance', 'getDefaultProviderForOperationType'],
    Drupal\ai\Plugin\ProviderProxy::class => ['__construct', '__call'],
    Drupal\ai_provider_openai\Plugin\AiProvider\OpenAiProvider::class => [
      '__construct', 'setConfiguration', 'getConfiguration', 'getAvailableConfiguration', 'getConfiguredModels',
    ],
    Drupal\ai\Service\FunctionCalling\FunctionCallPluginManager::class => ['__construct', 'createInstance'],
    Drupal\ai\Base\FunctionCallBase::class => [
      '__construct', 'create', 'populateValues', 'normalize', 'getReadableOutput', 'getStructuredOutput',
    ],
    Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface::class => [
      'execute', 'getReadableOutput', 'setOutput',
    ],
    ChatInput::class => ['__construct', 'setChatStructuredJsonSchema', 'getChatStructuredJsonSchema', 'setChatTools', 'getChatTools'],
  ]);
  $service_definitions = [
    'plugin.manager.ai_agents' => gate1_step02_service_definition($project_root . '/web/modules/contrib/ai_agents/ai_agents.services.yml', 'plugin.manager.ai_agents'),
    'ai.provider' => gate1_step02_service_definition($project_root . '/web/modules/contrib/ai/ai.services.yml', 'ai.provider'),
    'plugin.manager.ai.function_calls' => gate1_step02_service_definition($project_root . '/web/modules/contrib/ai/ai.services.yml', 'plugin.manager.ai.function_calls'),
    'ai_agents.private_temp_status_storage' => gate1_step02_service_definition($project_root . '/web/modules/contrib/ai_agents/ai_agents.services.yml', 'ai_agents.private_temp_status_storage'),
    'ai_agents.artifact_storage' => gate1_step02_service_definition($project_root . '/web/modules/contrib/ai_agents/ai_agents.services.yml', 'ai_agents.artifact_storage'),
  ];
  if ($provider_events !== 0 || $agent_request_events !== 0) {
    throw new RuntimeException('A model or agent request event occurred during the non-networked probe.');
  }

  return [
    'schema_version' => 1,
    'probe_version' => GATE1_STEP02_PROBE_VERSION,
    'status' => 'pass',
    'versions' => gate1_step02_composer_versions(),
    'chosen_runtime' => [
      'service_id' => 'plugin.manager.ai_agents',
      'service_class' => get_class($agent_manager),
      'plugin_definition_id' => $definition_id,
      'plugin_definition_custom_type' => $definition['custom_type'] ?? NULL,
      'config_entity_type' => 'ai_agent',
      'config_entity_class' => get_class($agent->getAiAgentEntity()),
      'instance_class' => get_class($agent),
      'interfaces' => $interfaces,
      'callable_entry_point' => 'determineSolvability',
      'final_output_method' => 'solve',
      'methods_verified' => $methods,
    ],
    'plugin_definition' => [
      'id' => $definition_id,
      'custom_type' => $definition['custom_type'] ?? NULL,
      'class' => $definition['class'] ?? NULL,
      'provider' => $definition['provider'] ?? NULL,
      'definition_keys' => array_values(array_keys($definition)),
    ],
    'config_entity' => [
      'entity_type_id' => $entity_type->id(),
      'class' => $entity_type->getClass(),
      'config_prefix' => $entity_type->getConfigPrefix(),
      'id_key' => $entity_type->getKey('id'),
      'label_key' => $entity_type->getKey('label'),
      'loaded_id' => $agent->getAiAgentEntity()->id(),
      'load_path' => "entity_type.manager->getStorage('ai_agent')->load(plugin_id)",
      'wrapped_by' => get_class($agent),
    ],
    'service_definitions' => $service_definitions,
    'reflection_surface' => $reflection_surface,
    'context_surface' => [
      'task_class' => Task::class,
      'methods' => ['setDescription', 'setComments', 'setFiles'],
      'account_boundary' => 'agent_bot',
      'unrelated_drupal_data_allowed' => FALSE,
    ],
    'tool_surface' => [
      'manager_service' => 'plugin.manager.ai.function_calls',
      'manager_class' => get_class($container->get('plugin.manager.ai.function_calls')),
      'attribute_class' => \Drupal\ai\Attribute\FunctionCall::class,
      'base_class' => \Drupal\ai\Base\FunctionCallBase::class,
      'interface' => \Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface::class,
      'selected_functions' => $rendered_functions,
      'required_tools_pending' => $agent->allRequiredToolsRan(),
      'selection_allowlist' => TRUE,
      'per_run_narrowing' => 'overrideFunctions',
      'parameter_actions' => ['only_allow', 'force_value'],
      'hidden_forced_parameter_supported' => TRUE,
      'provider_level_hard_tool_choice_supported' => FALSE,
    ],
    'future_adapters' => [
      'discover_targets',
      'get_image_context',
      'submit_recommendation',
      'get_recommendation_status',
    ],
    'provider' => [
      'manager_service' => 'ai.provider',
      'manager_class' => get_class($provider_manager),
      'proxy_class' => get_class($provider),
      'plugin_id' => $provider->getPluginId(),
      'plugin_class' => $provider_manager->getDefinition('openai')['class'] ?? NULL,
      'configured_key_reference_present' => $key_reference !== '',
      'configured_key_value_retained' => FALSE,
      'pinned_model_id' => GATE1_STEP02_MODEL,
      'agent_model_id' => $agent->getModelName(),
      'pinned_model_bound_to_agent' => $agent->getModelName() === GATE1_STEP02_MODEL,
      'model_catalog_query_performed' => FALSE,
      'explicit_configuration' => $provider->getConfiguration(),
      'temperature_configuration_supported' => is_array($temperature_definition),
      'active_chat_with_tools_default' => $provider_manager->getDefaultProviderForOperationType('chat_with_tools'),
      'default_path_accepted' => FALSE,
    ],
    'structured_output' => [
      'chat_input_method' => 'setChatStructuredJsonSchema',
      'normalized_schema' => $chat_input->getChatStructuredJsonSchema(),
      'raw_output_method' => 'solve',
      'agent_getStructuredOutput_is_raw_model_output' => FALSE,
    ],
    'trace_surface' => [
      'agent_methods' => ['getChatHistory', 'getToolResults'],
      'events' => [
        'ai_agents.request',
        'ai_agents.response',
        'ai_agents.tool_pre_executed',
        'ai_agents.tool_finished_executed',
        'ai_agents.finished_execution',
        PreGenerateResponseEvent::EVENT_NAME,
      ],
      'provider_error_event' => \Drupal\ai\Event\AiExceptionEvent::class,
      'provider_exception_returned_by_determineSolvability' => FALSE,
    ],
    'state_surface' => [
      'factory_service' => 'keyvalue',
      'factory_class' => get_class($keyvalue_factory),
      'collection' => 'agentic_harness_drupal_ai.run_state',
      'storage_class' => Drupal\Core\KeyValueStore\DatabaseStorage::class,
      'collection_opened' => FALSE,
      'write_performed' => FALSE,
      'wrapper_serializable_keys' => $serializable_keys,
      'restore_method' => 'fromArray',
      'private_status_storage_class' => get_class($private_status),
      'private_status_storage_accepted' => FALSE,
      'artifact_storage_class' => get_class($artifact_storage),
      'artifact_storage_accepted' => FALSE,
      'shared_runtime_storage' => FALSE,
    ],
    'inspected_source_sha256' => $source_hashes,
    'rejected_paths' => [
      'direct_provider_chat' => 'bypasses AI Agents execution and lifecycle',
      'agent_helper_runAiProvider' => 'lower-level provider helper, not config-agent execution',
      'ai_agents_explorer' => 'UI and private-session path',
      'existing_domain_agents' => 'wrong domain and tool surface',
      'direct_openai_sdk' => 'bypasses pinned Drupal AI stack',
      'private_shared_operation_write_path' => 'violates frozen shared boundary',
      'private_temp_status_storage' => 'session-bound, expirable, and skipped in CLI',
      'in_memory_artifact_storage' => 'not restart-persistent',
      'shared_runtime_state' => 'prohibited by Step 1.01',
    ],
    'limitations' => [
      'top_level_wrapper_configuration_must_also_be_set_on_provider_proxy',
      'required_tool_usage_is_loop_enforced_not_provider_hard_choice',
      'provider_exception_detail_requires_event_capture',
      'runtime_only_image_delivery_via_Task_setFiles_requires_Step_1_04_proof',
    ],
    'provider_pre_request_events_observed' => $provider_events,
    'agent_request_events_observed' => $agent_request_events,
    'model_call_performed' => FALSE,
    'network_call_performed' => FALSE,
    'drupal_write_performed' => FALSE,
    'raw_image_retained' => FALSE,
    'secret_retained' => FALSE,
    'framework_implementation_claimed' => FALSE,
  ];
}

try {
  switch ($mode) {
    case 'snapshot':
      gate1_step02_emit(gate1_step02_snapshot());
      break;

    case 'runtime':
      gate1_step02_emit(gate1_step02_runtime());
      break;

    default:
      throw new InvalidArgumentException('Usage: snapshot|runtime');
  }
}
catch (Throwable $exception) {
  fwrite(STDERR, '[ERROR] ' . $exception->getMessage() . PHP_EOL);
  exit(1);
}
