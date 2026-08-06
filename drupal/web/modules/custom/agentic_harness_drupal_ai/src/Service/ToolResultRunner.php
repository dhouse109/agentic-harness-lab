<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_drupal_ai\Service;

use Drupal\agentic_harness_tools\Exception\ImageContextException;
use Drupal\agentic_harness_tools\Exception\RecommendationStatusException;
use Drupal\agentic_harness_tools\Exception\RecommendationSubmissionException;
use Drupal\Component\Datetime\TimeInterface;
use Drupal\Component\Uuid\UuidInterface;
use Psr\Log\LoggerInterface;
use Symfony\Component\HttpKernel\Exception\AccessDeniedHttpException;

/**
 * Runs one direct delegation and maps it to the frozen tool-result envelope.
 */
final class ToolResultRunner {

  public function __construct(
    private readonly UuidInterface $uuid,
    private readonly TimeInterface $time,
    private readonly LoggerInterface $logger,
  ) {}

  /**
   * @param callable(): array<string, mixed> $delegate
   *   The direct shared-service call.
   *
   * @return array<string, mixed>
   *   A frozen shared tool-result envelope.
   */
  public function run(
    string $tool_name,
    string $correlation_id,
    callable $delegate,
  ): array {
    $correlation_id = $this->correlationId($correlation_id);
    try {
      return $this->success($tool_name, $correlation_id, $delegate());
    }
    catch (ImageContextException|RecommendationSubmissionException|RecommendationStatusException $exception) {
      return $this->error(
        $tool_name,
        $correlation_id,
        $exception->toolCode,
        $exception->getMessage(),
        $exception->retryable,
      );
    }
    catch (AccessDeniedHttpException) {
      return $this->error(
        $tool_name,
        $correlation_id,
        'ACCESS_DENIED',
        'The calling account is not authorized to use this adapter.',
        FALSE,
      );
    }
    catch (\Throwable $exception) {
      $this->logger->error(
        'Adapter {tool} failed with unexpected exception type {type}.',
        ['tool' => $tool_name, 'type' => $exception::class],
      );
      [$code, $message] = match ($tool_name) {
        'find_images_needing_review' => [
          'DISCOVERY_FAILED',
          'The deterministic discovery operation failed. Review Drupal logs for the local diagnostic.',
        ],
        'get_image_context' => [
          'CONTEXT_FAILED',
          'The deterministic context operation failed. Review Drupal logs for the local diagnostic.',
        ],
        'submit_recommendation' => [
          'SUBMISSION_FAILED',
          'The deterministic submission operation failed. Review Drupal logs for the local diagnostic.',
        ],
        'get_recommendation_status' => [
          'STATUS_FAILED',
          'The deterministic status operation failed. Review Drupal logs for the local diagnostic.',
        ],
        default => [
          'ADAPTER_FAILED',
          'The deterministic adapter operation failed. Review Drupal logs for the local diagnostic.',
        ],
      };
      return $this->error(
        $tool_name,
        $correlation_id,
        $code,
        $message,
        TRUE,
      );
    }
  }

  /**
   * @param array<string, mixed> $data
   *   Direct shared-service result data.
   *
   * @return array<string, mixed>
   *   Success envelope.
   */
  private function success(
    string $tool_name,
    string $correlation_id,
    array $data,
  ): array {
    return [
      'schema_version' => 1,
      'tool_name' => $tool_name,
      'ok' => TRUE,
      'timestamp' => gmdate('Y-m-d\TH:i:s\Z', $this->time->getCurrentTime()),
      'correlation_id' => $correlation_id,
      'data' => $data,
      'error' => NULL,
    ];
  }

  /**
   * @return array<string, mixed>
   *   Error envelope.
   */
  private function error(
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
      'timestamp' => gmdate('Y-m-d\TH:i:s\Z', $this->time->getCurrentTime()),
      'correlation_id' => $correlation_id,
      'data' => NULL,
      'error' => [
        'code' => $code,
        'message' => $message,
        'retryable' => $retryable,
      ],
    ];
  }

  private function correlationId(string $candidate): string {
    $candidate = trim($candidate);
    if ($candidate !== '' && strlen($candidate) <= 128) {
      return $candidate;
    }
    return 'function-call-' . $this->uuid->generate();
  }

}
