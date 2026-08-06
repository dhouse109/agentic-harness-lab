<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall;

use Drupal\agentic_harness_drupal_ai\Service\ToolResultRunner;
use Drupal\agentic_harness_tools\Service\RecommendationSubmitter;
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
 * Delegates recommendation submission to the certified shared submitter.
 */
#[FunctionCall(
  id: 'submit_recommendation',
  function_name: 'submit_recommendation',
  name: 'Submit alt-text recommendation',
  description: 'Submits exactly one validated recommendation object to the shared pending review queue.',
  group: 'submit_recommendation',
  module_dependencies: ['agentic_harness_tools'],
  context_definitions: [
    'recommendation' => new ContextDefinition(
      data_type: 'array',
      label: new TranslatableMarkup('Recommendation'),
      description: new TranslatableMarkup('Exactly one object conforming to recommendation.schema.json.'),
      required: TRUE,
    ),
  ],
)]
final class SubmitRecommendation extends FunctionCallBase implements ExecutableFunctionCallInterface {

  private mixed $recommendationInput = NULL;

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    ContextDefinitionNormalizer $context_definition_normalizer,
    AiDataTypeConverterPluginManager $data_type_converter_manager,
    private readonly AccountProxyInterface $currentUser,
    private readonly RecommendationSubmitter $submitter,
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
      $container->get('agentic_harness_tools.recommendation_submitter'),
      $container->get('agentic_harness_drupal_ai.tool_result_runner'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function normalize(): ToolsFunctionInput {
    $function = parent::normalize();
    $property = $function->getPropertyByName('recommendation');
    if ($property === NULL) {
      throw new \LogicException('The recommendation input definition is unavailable.');
    }
    $property->setType('object');
    return $function;
  }

  /**
   * {@inheritdoc}
   */
  public function setContextValue($name, $value) {
    if ($name === 'recommendation') {
      $this->recommendationInput = $value;
      return $this;
    }
    return parent::setContextValue($name, $value);
  }

  /**
   * {@inheritdoc}
   */
  public function execute(): void {
    $envelope = $this->resultRunner->run(
      'submit_recommendation',
      $this->getToolsId(),
      function (): array {
        $this->assertPermission();
        $recommendation = $this->recommendationInput;
        if (!is_array($recommendation) || array_is_list($recommendation)) {
          throw new \InvalidArgumentException('The recommendation input must be one object.');
        }
        return $this->submitter->submit($recommendation);
      },
    );
    $this->finish($envelope);
  }

  private function assertPermission(): void {
    if (!$this->currentUser->hasPermission('create alt_text_suggestion content')) {
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
