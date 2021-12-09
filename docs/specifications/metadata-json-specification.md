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

Each Item's metadata (which will be identified in the message body
"MetadataLocation" field as specified in adr-0003) will be provided in a single
JSON file that consists of an array of objects, each object representing a
single field in DSpace. It is up to the submitting system to ensure that the
field names are accurate and the field values are compliant with DSpace
requirements, this system will simply parse and post all of the fields as
provided.

The metadata file should be structured as follows:

```
{
  "metadata": [
    {
      "key": "<Name of the DSpace metadata field in qualified Dublin Core format, e.g. 'dc.title'",
      "value": "<String value of the field, e.g. 'A Very Important Thesis'",
      "language": "<Optional - language of the field's value>"
    },
    {
      ...repeat for all of the item's metadata fields...
    }
  ]
}
```
