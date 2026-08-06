<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall;

use Drupal\agentic_harness_drupal_ai\Service\ToolResultRunner;
use Drupal\agentic_harness_tools\Service\ImageReviewFinder;
use Drupal\ai\Attribute\FunctionCall;
use Drupal\ai\Base\FunctionCallBase;
use Drupal\ai\PluginManager\AiDataTypeConverterPluginManager;
use Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface;
use Drupal\ai\Service\FunctionCalling\FunctionCallInterface;
use Drupal\ai\Utility\ContextDefinitionNormalizer;
use Drupal\Core\Session\AccountProxyInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpKernel\Exception\AccessDeniedHttpException;

/**
 * Delegates target discovery to the certified shared finder.
 */
#[FunctionCall(
  id: 'discover_targets',
  function_name: 'discover_targets',
  name: 'Discover image review targets',
  description: 'Returns the frozen ordered image-field targets needing review. This function accepts no business input.',
  group: 'discover_targets',
  module_dependencies: ['agentic_harness_tools'],
)]
final class DiscoverTargets extends FunctionCallBase implements ExecutableFunctionCallInterface {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    ContextDefinitionNormalizer $context_definition_normalizer,
    AiDataTypeConverterPluginManager $data_type_converter_manager,
    private readonly AccountProxyInterface $currentUser,
    private readonly ImageReviewFinder $finder,
    private readonly ToolResultRunner $resultRunner,
  ) {
    parent::__construct(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $context_definition_normalizer,
      $data_type_converter_manager,
    );
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition): FunctionCallInterface|static {
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('ai.context_definition_normalizer'),
      $container->get('plugin.manager.ai_data_type_converter'),
      $container->get('current_user'),
      $container->get('agentic_harness_tools.image_review_finder'),
      $container->get('agentic_harness_drupal_ai.tool_result_runner'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function execute(): void {
    $envelope = $this->resultRunner->run(
      'find_images_needing_review',
      $this->getToolsId(),
      function (): array {
        $this->assertPermission();
        $targets = $this->finder->find();
        return [
          'targets' => $targets,
          'total_count' => count($targets),
        ];
      },
    );
    $this->finish($envelope);
  }

  private function assertPermission(): void {
    if (!$this->currentUser->hasPermission('use agentic harness discovery tools')) {
      throw new AccessDeniedHttpException();
    }
  }

  /**
   * @param array<string, mixed> $envelope
   *   Frozen tool-result envelope.
   */
  private function finish(array $envelope): void {
    $this->setStructuredOutput($envelope);
    $this->setOutput(json_encode(
      $envelope,
      JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
    ));
  }

}
