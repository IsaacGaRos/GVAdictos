# Study features backend status

- Checked at: 2026-06-18T15:13:16
- DB unchanged during report: True
- Ready for UI: False
- Migration status: pending
- Missing base tables: none
- Existing study tables: study_annotations
- Missing study feature tables: study_article_notes, study_highlights, study_progress, study_marks, study_last_reviews

## Counts

- study_article_notes: missing
- study_highlights: missing
- study_progress: missing
- study_marks: missing
- study_last_reviews: missing
- doubt marks: missing
- important marks: missing
- latest review: none

## Referential integrity

- notes_missing_articles: not checked
- highlights_missing_articles: not checked
- progress_missing_articles: not checked
- progress_missing_topics: not checked
- marks_missing_articles: not checked
- marks_missing_topics: not checked
- reviews_missing_articles: not checked
- reviews_missing_topics: not checked

## Progress Average By Topic

- none

## Recommendation

Run scripts/migrate_study_features.py --dry-run first; apply only after explicit approval.
