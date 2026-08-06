<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall;

use Drupal\agentic_harness_drupal_ai\Service\ToolResultRunner;
use Drupal\agentic_harness_tools\Service\RecommendationStatusProvider;
use Drupal\ai\Attribute\FunctionCall;
use Drupal\ai\Base\FunctionCallBase;
use Drupal\ai\OperationType\Chat\Tools\ToolsFunctionInput;
use Drupal\ai\PluginManager\AiDataTypeConverterPluginManager;
use Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface;
use Drupal\ai\Service\FunctionCalling\FunctionCallInterface;
use Drupal\ai\Utility\ContextDefinitionNormalizer;
use Drupal\Core\Plugin\Context\ContextDefinition;
use Drupal\Core\Session\AccountProxyInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpKernel\Exception\AccessDeniedHttpException;

/**
 * Delegates read-only status projection to the certified shared provider.
 */
#[FunctionCall(
  id: 'get_recommendation_status',
  function_name: 'get_recommendation_status',
  name: 'Get recommendation status',
  description: 'Returns the read-only status of exactly one recommendation identified by a positive node ID or UUID.',
  group: 'get_recommendation_status',
  module_dependencies: ['agentic_harness_tools'],
  context_definitions: [
    'recommendation_id' => new ContextDefinition(
      data_type: 'string',
      label: new TranslatableMarkup('Recommendation identifier'),
      description: new TranslatableMarkup('Exactly one positive node ID or UUID.'),
      required: TRUE,
    ),
  ],
)]
final class GetRecommendationStatus extends FunctionCallBase implements ExecutableFunctionCallInterface {

  private const IDENTIFIER_PATTERN = '^(?:[1-9][0-9]{0,18}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})$';

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    ContextDefinitionNormalizer $context_definition_normalizer,
    AiDataTypeConverterPluginManager $data_type_converter_manager,
    private readonly AccountProxyInterface $currentUser,
    private readonly RecommendationStatusProvider $statusProvider,
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
      $container->get('agentic_harness_tools.recommendation_status_provider'),
      $container->get('agentic_harness_drupal_ai.tool_result_runner'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function normalize(): ToolsFunctionInput {
    $function = parent::normalize();
    $property = $function->getPropertyByName('recommendation_id');
    if ($property === NULL) {
      throw new \LogicException('The recommendation identifier definition is unavailable.');
    }
    $property->setPattern(self::IDENTIFIER_PATTERN);
    return $function;
  }

  /**
   * {@inheritdoc}
   */
  public function execute(): void {
    $envelope = $this->resultRunner->run(
      'get_recommendation_status',
      $this->getToolsId(),
      function (): array {
        $this->assertPermission();
        return $this->statusProvider->get((string) $this->getContextValue('recommendation_id'));
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
