<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Service;

use Drupal\agentic_harness_tools\Exception\RecommendationSubmissionException;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccountProxyInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;

/**
 * Deterministically validates one assembled recommendation.
 *
 * This service is model-free. It validates the frozen schema and verifies the
 * exact current Drupal field usage before any recommendation record is saved.
 */
final class RecommendationValidator {

  public const VERSION = 'gate05-validator-1.0.0';

  private const RECOMMENDATION_KEYS = [
    'schema_version',
    'target',
    'proposed_alt_text',
    'source_framework',
    'run_id',
    'evidence_hash',
    'validator_version',
  ];

  private const TARGET_KEYS = [
    'schema_version',
    'sequence',
    'node_uuid',
    'revision_id',
    'field_name',
    'delta',
    'file_uuid',
    'target_state',
    'existing_alt',
  ];

  private const SOURCE_FRAMEWORKS = [
    'drupal_ai',
    'langgraph',
    'crewai',
  ];

  private const GENERIC_ALT_VALUES = [
    'image',
    'photo',
    'picture',
    'graphic',
    'illustration',
    'icon',
    'placeholder',
    'test image',
    'article image',
    'supporting image',
    'primary image',
  ];

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly AccountProxyInterface $currentUser,
    private readonly ImageReviewFinder $finder,
  ) {}

  /**
   * @param array<string, mixed> $recommendation
   *   One recommendation conforming to recommendation.schema.json.
   *
   * @return array{
   *   recommendation: array<string, mixed>,
   *   target_node: \Drupal\node\NodeInterface,
   *   target_file: \Drupal\file\FileInterface
   * }
   */
  public function validate(array $recommendation): array {
    $this->assertExactKeys(
      $recommendation,
      self::RECOMMENDATION_KEYS,
      'INVALID_RECOMMENDATION',
      'Recommendation keys do not match recommendation.schema.json.',
    );

    if ($recommendation['schema_version'] !== 1) {
      throw $this->invalid(
        'INVALID_RECOMMENDATION',
        'Recommendation schema_version must be 1.',
      );
    }

    if (!is_array($recommendation['target']) || array_is_list($recommendation['target'])) {
      throw $this->invalid('INVALID_TARGET', 'Target must be one JSON object.');
    }
    $target = $this->validateTargetShape($recommendation['target']);

    $source = $recommendation['source_framework'];
    if (!is_string($source) || !in_array($source, self::SOURCE_FRAMEWORKS, TRUE)) {
      throw $this->invalid(
        'INVALID_SOURCE_FRAMEWORK',
        'source_framework must be drupal_ai, langgraph, or crewai.',
      );
    }

    $run_id = $recommendation['run_id'];
    if (
      !is_string($run_id)
      || preg_match(
        '/^(drupal_ai|langgraph|crewai)-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$/',
        $run_id,
      ) !== 1
    ) {
      throw $this->invalid(
        'INVALID_RUN_ID',
        'run_id does not match the frozen experiment format.',
      );
    }
    if (!str_starts_with($run_id, $source . '-')) {
      throw $this->invalid(
        'RUN_ID_MISMATCH',
        'run_id prefix does not match source_framework.',
      );
    }

    $evidence_hash = $recommendation['evidence_hash'];
    if (
      !is_string($evidence_hash)
      || preg_match('/^sha256:[a-f0-9]{64}$/', $evidence_hash) !== 1
    ) {
      throw $this->invalid(
        'INVALID_EVIDENCE_HASH',
        'evidence_hash must be a lowercase SHA-256 identifier.',
      );
    }

    $validator_version = $recommendation['validator_version'];
    if (
      !is_string($validator_version)
      || preg_match('/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/', $validator_version) !== 1
    ) {
      throw $this->invalid(
        'INVALID_VALIDATOR_VERSION',
        'validator_version contains unsupported characters or length.',
      );
    }

    if (!is_string($recommendation['proposed_alt_text'])) {
      throw $this->invalid('ALT_TEXT_EMPTY', 'proposed_alt_text must be a string.');
    }
    $proposed_alt = trim($recommendation['proposed_alt_text']);
    if ($proposed_alt === '') {
      throw $this->invalid('ALT_TEXT_EMPTY', 'proposed_alt_text is empty after trimming.');
    }
    if (mb_strlen($proposed_alt) > 250) {
      throw $this->invalid(
        'ALT_TEXT_TOO_LONG',
        'proposed_alt_text exceeds the frozen 250-character experiment limit.',
      );
    }
    if (
      preg_match(
        '/^(?:here(?:[’\']s| is)\b|alt\s*text\s*:|proposed\s+alt\s*text\s*:)/iu',
        $proposed_alt,
      ) === 1
    ) {
      throw $this->invalid(
        'ALT_TEXT_PREAMBLE',
        'proposed_alt_text contains an obvious model preamble.',
      );
    }

    [$node, $file, $current_alt] = $this->verifyCurrentTarget($target);

    $normalized_proposed = $this->normalize($proposed_alt);
    $normalized_current = $this->normalize($current_alt);
    if ($normalized_current !== '' && $normalized_proposed === $normalized_current) {
      throw $this->invalid(
        'ALT_TEXT_DUPLICATE',
        'proposed_alt_text duplicates the current alt text.',
      );
    }

    if ($this->isFilenameEcho($normalized_proposed, $file->getFilename())) {
      throw $this->invalid(
        'ALT_TEXT_FILENAME_ECHO',
        'proposed_alt_text is a filename or filename echo.',
      );
    }

    if (
      in_array($normalized_proposed, self::GENERIC_ALT_VALUES, TRUE)
      || preg_match(
        '/^(image|photo|picture|graphic|illustration)(\s+\d+)?(?:\.(?:png|jpe?g|gif|webp))?$/u',
        $normalized_proposed,
      ) === 1
    ) {
      throw $this->invalid(
        'ALT_TEXT_GENERIC',
        'proposed_alt_text is a generic placeholder.',
      );
    }

    $normalized = $recommendation;
    $normalized['target'] = $target;
    $normalized['proposed_alt_text'] = $proposed_alt;

    return [
      'recommendation' => $normalized,
      'target_node' => $node,
      'target_file' => $file,
    ];
  }

  /**
   * @param array<string, mixed> $target
   *
   * @return array<string, mixed>
   */
  private function validateTargetShape(array $target): array {
    $this->assertExactKeys(
      $target,
      self::TARGET_KEYS,
      'INVALID_TARGET',
      'Target keys do not match target.schema.json.',
    );

    if (
      $target['schema_version'] !== 1
      || !is_int($target['sequence'])
      || $target['sequence'] < 1
      || $target['sequence'] > 12
      || !is_string($target['node_uuid'])
      || !$this->isValidUuid($target['node_uuid'])
      || !is_int($target['revision_id'])
      || $target['revision_id'] < 1
      || $target['field_name'] !== 'field_image'
      || !is_int($target['delta'])
      || $target['delta'] < 0
      || !is_string($target['file_uuid'])
      || !$this->isValidUuid($target['file_uuid'])
      || !in_array($target['target_state'], ['missing', 'poor'], TRUE)
      || !(is_string($target['existing_alt']) || $target['existing_alt'] === NULL)
    ) {
      throw $this->invalid(
        'INVALID_TARGET',
        'Target values do not conform to target.schema.json.',
      );
    }

    return $target;
  }

  /**
   * @param array<string, mixed> $target
   *
   * @return array{
   *   0: \Drupal\node\NodeInterface,
   *   1: \Drupal\file\FileInterface,
   *   2: string
   * }
   */
  private function verifyCurrentTarget(array $target): array {
    $targets = $this->finder->find();
    $index = $target['sequence'] - 1;
    if (
      !isset($targets[$index])
      || $this->canonicalJson($targets[$index]) !== $this->canonicalJson($target)
    ) {
      throw $this->stale();
    }

    $node_storage = $this->entityTypeManager->getStorage('node');
    $node_matches = $node_storage->loadByProperties(['uuid' => $target['node_uuid']]);
    $node = reset($node_matches);
    if (!$node instanceof NodeInterface || !$node->access('view', $this->currentUser)) {
      throw new RecommendationSubmissionException(
        'TARGET_UNAVAILABLE',
        'The target Article is unavailable to the calling account.',
        403,
      );
    }
    if (
      (int) $node->getRevisionId() !== $target['revision_id']
      || !$node->hasField($target['field_name'])
    ) {
      throw $this->stale();
    }

    $field = $node->get($target['field_name']);
    if (!$field->access('view', $this->currentUser)) {
      throw new RecommendationSubmissionException(
        'TARGET_UNAVAILABLE',
        'The target field is unavailable to the calling account.',
        403,
      );
    }
    if (
      $field->getFieldDefinition()->getType() !== 'image'
      || !$field->offsetExists($target['delta'])
    ) {
      throw $this->stale();
    }

    $item = $field->get($target['delta']);
    $file = $item?->entity;
    if (!$file instanceof FileInterface || !$file->access('view', $this->currentUser)) {
      throw new RecommendationSubmissionException(
        'TARGET_UNAVAILABLE',
        'The target image is unavailable to the calling account.',
        403,
      );
    }
    if ($file->uuid() !== $target['file_uuid']) {
      throw $this->stale();
    }

    $current_alt = isset($item->alt) ? (string) $item->alt : '';
    if (
      $current_alt !== (string) ($target['existing_alt'] ?? '')
      || (int) $node->getRevisionId() !== $target['revision_id']
    ) {
      throw $this->stale();
    }

    return [$node, $file, $current_alt];
  }

  /**
   * @param array<string, mixed> $value
   * @param array<int, string> $expected
   */
  private function assertExactKeys(
    array $value,
    array $expected,
    string $code,
    string $message,
  ): void {
    $actual = array_keys($value);
    sort($actual);
    sort($expected);
    if ($actual !== $expected) {
      throw $this->invalid($code, $message);
    }
  }

  private function isFilenameEcho(string $normalized_alt, string $filename): bool {
    $stem = pathinfo($filename, PATHINFO_FILENAME);
    $variants = [
      $this->normalize($filename),
      $this->normalize($stem),
      $this->normalize(str_replace(['-', '_'], ' ', $stem)),
    ];
    if (in_array($normalized_alt, $variants, TRUE)) {
      return TRUE;
    }

    foreach ($variants as $variant) {
      if (
        $variant !== ''
        && preg_match(
          '/^(?:image|photo|picture|graphic|illustration)(?:\s+of)?\s+'
            . preg_quote($variant, '/')
            . '$/u',
          $normalized_alt,
        ) === 1
      ) {
        return TRUE;
      }
    }
    return FALSE;
  }

  private function normalize(string $value): string {
    $value = trim($value);
    $value = preg_replace('/\s+/u', ' ', $value) ?? $value;
    return mb_strtolower($value);
  }

  private function isValidUuid(string $value): bool {
    return preg_match(
      '/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i',
      $value,
    ) === 1;
  }

  private function canonicalJson(mixed $value): string {
    return json_encode(
      $this->sortValue($value),
      JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
    );
  }

  private function sortValue(mixed $value): mixed {
    if (!is_array($value)) {
      return $value;
    }
    if (array_is_list($value)) {
      return array_map(fn(mixed $item): mixed => $this->sortValue($item), $value);
    }
    ksort($value);
    foreach ($value as $key => $item) {
      $value[$key] = $this->sortValue($item);
    }
    return $value;
  }

  private function invalid(
    string $code,
    string $message,
  ): RecommendationSubmissionException {
    return new RecommendationSubmissionException($code, $message, 422);
  }

  private function stale(): RecommendationSubmissionException {
    return new RecommendationSubmissionException(
      'TARGET_STALE',
      'The target no longer matches the current authorized field usage.',
      409,
    );
  }

}
