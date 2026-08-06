<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_drupal_ai\Plugin\AiFunctionCall;

use Drupal\agentic_harness_drupal_ai\Service\ToolResultRunner;
use Drupal\agentic_harness_tools\Service\ImageContextProvider;
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
 * Delegates exact target context retrieval to the certified shared provider.
 */
#[FunctionCall(
  id: 'get_image_context',
  function_name: 'get_image_context',
  name: 'Get permitted image context',
  description: 'Returns permitted Article and image context for exactly one frozen target object.',
  group: 'get_image_context',
  module_dependencies: ['agentic_harness_tools'],
  context_definitions: [
    'target' => new ContextDefinition(
      data_type: 'array',
      label: new TranslatableMarkup('Target'),
      description: new TranslatableMarkup('Exactly one object conforming to target.schema.json.'),
      required: TRUE,
    ),
  ],
)]
final class GetImageContext extends FunctionCallBase implements ExecutableFunctionCallInterface {

  private mixed $targetInput = NULL;

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    ContextDefinitionNormalizer $context_definition_normalizer,
    AiDataTypeConverterPluginManager $data_type_converter_manager,
    private readonly AccountProxyInterface $currentUser,
    private readonly ImageContextProvider $contextProvider,
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
      $container->get('agentic_harness_tools.image_context_provider'),
      $container->get('agentic_harness_drupal_ai.tool_result_runner'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function normalize(): ToolsFunctionInput {
    $function = parent::normalize();
    $property = $function->getPropertyByName('target');
    if ($property === NULL) {
      throw new \LogicException('The target input definition is unavailable.');
    }
    $property->setType('object');
    return $function;
  }

  /**
   * {@inheritdoc}
   */
  public function setContextValue($name, $value) {
    if ($name === 'target') {
      $this->targetInput = $value;
      return $this;
    }
    return parent::setContextValue($name, $value);
  }

  /**
   * {@inheritdoc}
   */
  public function execute(): void {
    $envelope = $this->resultRunner->run(
      'get_image_context',
      $this->getToolsId(),
      function (): array {
        $this->assertPermission();
        $target = $this->targetInput;
        if (!is_array($target) || array_is_list($target)) {
          throw new \InvalidArgumentException('The target input must be one object.');
        }
        return $this->contextProvider->get($target);
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
