# Metadata JSON Specification

## Context

Multiple external applications will submit DSpace item-level metadata as JSON
files that need to be processed by this system, so we need a specification they
can follow to create consistent metadata files with a known structure for this
application to handle.

All applications submitting items to this service will need to follow this specification.

All metadata files submitted following this specification should be successfully parsed and processed by the DSpace Submission Service. Note that this does not guarantee the submission will be successfully added to DSpace.

Messages that do not follow this specification will be rejected and sent to the result queue with a useful error message for the submitting application to handle.

## Specification

Each item submitted to the dspace-submission-service for publishing must include a JSON
metadata file containing all of the metadata for that item. This metadata file will be
identified in the submission message as documented in the submission message
specification.

The JSON metadata file must consist of a single 'metadata' object containing array of
objects, each of which represents a single DSpace metadata field, as described below.
It is up to the submitting system to ensure that the field names are accurate and the
field values are compliant with DSpace requirements. This system will simply parse and
post all of the fields as provided in the JSON file.

```
{
  "metadata": [
    {
      "key": "Name of the DSpace metadata field in qualified Dublin Core format, e.g. 'dc.title'",
      "value": "String value of the field, e.g. 'A Very Important Thesis'",
      "language": "Optional - language of the field's value"
    },
    {
      The above object may be repeated as needed for each field in the item's
      metadata. Repeatable fields must include a single object structured as above
      for each instance of that field in the metadata.

      NOTE: Do not include empty or null fields in this file. If the item does not have
      a value for a given metadata field, simply omit that field from the JSON.
      Including fields with empty or null values will result in DSpace errors.
    }
  ]
}
```

## Examples

### Good Metadata File Example

```json
{
  "metadata": [
    {
      "key": "dc.title",
      "value": "A Very Important Thesis",
      "language": "en_US"
    },
    {
      "key": "dc.contributor.author",
      "value": "Jane Q. Smith"
    },
    {
      "key": "dc.contributor.author",
      "value": "John S. Doe"
    }
  ]
}
```

### Bad Metadata File Example

```json
{
  "metadata": [
    {
      "key": "dc.title",
      "value": "A Very Important Thesis",
      "language": "en_US"
    },
    {
      "key": "dc.contributor.author",
      "value": ["Jane Q. Smith", "John S. Doe"]
    },
    {
      "key": "dc.description.abstract",
      "value": null
    }
  ]
}
```
