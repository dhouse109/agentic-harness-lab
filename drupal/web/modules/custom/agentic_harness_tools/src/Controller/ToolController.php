<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Controller;

use Drupal\agentic_harness_tools\Exception\ImageContextException;
use Drupal\agentic_harness_tools\Exception\RecommendationStatusException;
use Drupal\agentic_harness_tools\Exception\RecommendationSubmissionException;
use Drupal\agentic_harness_tools\Service\ImageContextProvider;
use Drupal\agentic_harness_tools\Service\ImageReviewFinder;
use Drupal\agentic_harness_tools\Service\RecommendationStatusProvider;
use Drupal\agentic_harness_tools\Service\RecommendationSubmitter;
use Drupal\Component\Uuid\UuidInterface;
use Drupal\Core\Controller\ControllerBase;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;

/**
 * HTTP boundary for deterministic shared substrate operations.
 */
final class ToolController extends ControllerBase {

  public function __construct(
    private readonly ImageReviewFinder $finder,
    private readonly ImageContextProvider $contextProvider,
    private readonly RecommendationSubmitter $recommendationSubmitter,
    private readonly RecommendationStatusProvider $recommendationStatusProvider,
    private readonly UuidInterface $uuid,
  ) {}

  public static function create(ContainerInterface $container): self {
    return new self(
      $container->get('agentic_harness_tools.image_review_finder'),
      $container->get('agentic_harness_tools.image_context_provider'),
      $container->get('agentic_harness_tools.recommendation_submitter'),
      $container->get('agentic_harness_tools.recommendation_status_provider'),
      $container->get('uuid'),
    );
  }

  public function findImagesNeedingReview(Request $request): JsonResponse {
    $tool_name = 'find_images_needing_review';
    $correlation_id = $this->correlationId($request);

    try {
      $targets = $this->finder->find();
      $missing = count(array_filter($targets, static fn(array $target): bool => $target['target_state'] === 'missing'));
      $poor = count(array_filter($targets, static fn(array $target): bool => $target['target_state'] === 'poor'));

      if (count($targets) !== 12 || $missing !== 9 || $poor !== 3) {
        return new JsonResponse($this->errorEnvelope(
          $tool_name,
          $correlation_id,
          'DISCOVERY_CARDINALITY_MISMATCH',
          sprintf('Expected 12 targets (9 missing, 3 poor); discovered %d (%d missing, %d poor).', count($targets), $missing, $poor),
          FALSE,
        ), 409);
      }

      return new JsonResponse($this->successEnvelope(
        $tool_name,
        $correlation_id,
        [
          'targets' => $targets,
          'total_count' => 12,
        ],
      ), 200, ['Cache-Control' => 'no-store, private']);
    }
    catch (\Throwable $exception) {
      $this->getLogger('agentic_harness_tools')->error(
        'find_images_needing_review failed: @message',
        ['@message' => $exception->getMessage()],
      );
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        'DISCOVERY_FAILED',
        'The deterministic discovery operation failed. Review Drupal logs for the local diagnostic.',
        TRUE,
      ), 500);
    }
  }

  public function getImageContext(Request $request): JsonResponse {
    $tool_name = 'get_image_context';
    $correlation_id = $this->correlationId($request);

    try {
      $decoded = $this->decodeObject($request, 'INVALID_TARGET');
      $context = $this->contextProvider->get($decoded);
      return new JsonResponse(
        $this->successEnvelope($tool_name, $correlation_id, $context),
        200,
        ['Cache-Control' => 'no-store, private'],
      );
    }
    catch (\JsonException) {
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        'MALFORMED_JSON',
        'The request body must contain valid JSON.',
        FALSE,
      ), 400);
    }
    catch (ImageContextException $exception) {
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        $exception->toolCode,
        $exception->getMessage(),
        $exception->retryable,
      ), $exception->httpStatus);
    }
    catch (\Throwable $exception) {
      $this->getLogger('agentic_harness_tools')->error(
        'get_image_context failed: @message',
        ['@message' => $exception->getMessage()],
      );
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        'CONTEXT_FAILED',
        'The deterministic context operation failed. Review Drupal logs for the local diagnostic.',
        TRUE,
      ), 500);
    }
  }

  public function submitRecommendation(Request $request): JsonResponse {
    $tool_name = 'submit_recommendation';
    $correlation_id = $this->correlationId($request);

    try {
      $decoded = $this->decodeObject($request, 'INVALID_RECOMMENDATION');
      $result = $this->recommendationSubmitter->submit($decoded);
      return new JsonResponse(
        $this->successEnvelope($tool_name, $correlation_id, $result),
        200,
        ['Cache-Control' => 'no-store, private'],
      );
    }
    catch (\JsonException) {
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        'MALFORMED_JSON',
        'The request body must contain valid JSON.',
        FALSE,
      ), 400);
    }
    catch (RecommendationSubmissionException $exception) {
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        $exception->toolCode,
        $exception->getMessage(),
        $exception->retryable,
      ), $exception->httpStatus);
    }
    catch (\Throwable $exception) {
      $this->getLogger('agentic_harness_tools')->error(
        'submit_recommendation failed: @message',
        ['@message' => $exception->getMessage()],
      );
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        'SUBMISSION_FAILED',
        'The deterministic submission operation failed. Review Drupal logs for the local diagnostic.',
        TRUE,
      ), 500);
    }
  }

  public function getRecommendationStatus(
    string $recommendation_id,
    Request $request,
  ): JsonResponse {
    $tool_name = 'get_recommendation_status';
    $correlation_id = $this->correlationId($request);

    try {
      $result = $this->recommendationStatusProvider->get($recommendation_id);
      return new JsonResponse(
        $this->successEnvelope($tool_name, $correlation_id, $result),
        200,
        ['Cache-Control' => 'no-store, private'],
      );
    }
    catch (RecommendationStatusException $exception) {
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        $exception->toolCode,
        $exception->getMessage(),
        $exception->retryable,
      ), $exception->httpStatus);
    }
    catch (\Throwable $exception) {
      $this->getLogger('agentic_harness_tools')->error(
        'get_recommendation_status failed: @message',
        ['@message' => $exception->getMessage()],
      );
      return new JsonResponse($this->errorEnvelope(
        $tool_name,
        $correlation_id,
        'STATUS_FAILED',
        'The deterministic status operation failed. Review Drupal logs for the local diagnostic.',
        TRUE,
      ), 500);
    }
  }

  /**
   * @return array<string, mixed>
   */
  private function decodeObject(
    Request $request,
    string $invalid_code,
  ): array {
    $decoded = json_decode(
      $request->getContent(),
      TRUE,
      512,
      JSON_THROW_ON_ERROR,
    );
    if (!is_array($decoded) || array_is_list($decoded)) {
      if ($invalid_code === 'INVALID_TARGET') {
        throw new ImageContextException(
          $invalid_code,
          'The request body must be one target object.',
          422,
        );
      }
      throw new RecommendationSubmissionException(
        $invalid_code,
        'The request body must be one recommendation object.',
        422,
      );
    }
    return $decoded;
  }

  private function correlationId(Request $request): string {
    $candidate = trim((string) $request->headers->get('X-Correlation-ID', ''));
    if ($candidate !== '' && preg_match('/^[A-Za-z0-9._:-]{1,128}$/', $candidate) === 1) {
      return $candidate;
    }
    return 'tool-' . $this->uuid->generate();
  }

  /**
   * @param array<string, mixed> $data
   *
   * @return array<string, mixed>
   */
  private function successEnvelope(string $tool_name, string $correlation_id, array $data): array {
    return [
      'schema_version' => 1,
      'tool_name' => $tool_name,
      'ok' => TRUE,
      'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
      'correlation_id' => $correlation_id,
      'data' => $data,
      'error' => NULL,
    ];
  }

  /**
   * @return array<string, mixed>
   */
  private function errorEnvelope(
    string $tool_name,
    string $correlation_id,
    string $code,
    string $message,
    bool $retryable,
  ): array {
    return [
      'schema_version' => 1,
      'tool_name' => $tool_name,
      'ok' => FALSE,
      'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
      'correlation_id' => $correlation_id,
      'data' => NULL,
      'error' => [
        'code' => $code,
        'message' => $message,
        'retryable' => $retryable,
      ],
    ];
  }

}
