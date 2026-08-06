<?php

declare(strict_types=1);

use Drupal\ai_agents\PluginInterfaces\ConfigAiAgentInterface;

/**
 * Model-free pre-image wrapper serialization compatibility probe.
 *
 * This script intentionally does not create a Task, image, provider request, or config entity.
 */
$container = \Drupal::getContainer();
$manager = $container->get('plugin.manager.ai_agents');
$provider_manager = $container->get('ai.provider');
$agent = $manager->createInstance('content_type_agent_triage');
if (!$agent instanceof ConfigAiAgentInterface) {
  throw new RuntimeException('The installed config-agent wrapper is unavailable.');
}
$provider = $provider_manager->createInstance('openai');
$provider->setConfiguration(['temperature' => 0.0]);
$agent->setAiProvider($provider);
$agent->setModelName('gpt-4.1-mini-2025-04-14');
$agent->setAiConfiguration(['temperature' => 0.0]);
$agent->overrideFunctions(['tools' => [], 'tool_usage_limits' => [], 'tool_settings' => []]);
$checkpoint = $agent->toArray();

$encoded = json_encode($checkpoint, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
$unsafe = preg_match('/(?:data:image|Authorization\\s*:|Bearer\\s+|sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9+\\/]{128,}={0,2})/i', $encoded) === 1;
if ($unsafe || !empty($checkpoint['chat_history'])) {
  throw new RuntimeException('Pre-image wrapper checkpoint contains prohibited serialized material.');
}
$restored = $manager->createInstance('content_type_agent_triage');
if (!$restored instanceof ConfigAiAgentInterface) {
  throw new RuntimeException('The restored config-agent wrapper is unavailable.');
}
$restored->fromArray($checkpoint);
if ($restored->getModelName() !== 'gpt-4.1-mini-2025-04-14' || $restored->getAiConfiguration() !== ['temperature' => 0.0]) {
  throw new RuntimeException('Pre-image wrapper checkpoint did not preserve safe metadata.');
}
print json_encode([
  'schema_version' => 1,
  'status' => 'pass',
  'checkpoint_stage' => 'pre_task_pre_image_pre_provider',
  'keys' => array_keys($checkpoint),
  'provider_id' => $checkpoint['provider_id'] ?? NULL,
  'model_name' => $checkpoint['model_name'] ?? NULL,
  'ai_configuration' => $checkpoint['ai_configuration'] ?? NULL,
  'chat_history_empty' => empty($checkpoint['chat_history']),
  'files_or_images_present' => FALSE,
  'base64_or_data_url_present' => FALSE,
  'credential_or_authorization_present' => FALSE,
  'from_array_restored' => TRUE,
  'provider_request_count' => 0,
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;
