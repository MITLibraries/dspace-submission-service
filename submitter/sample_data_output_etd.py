from submitter.sqs import output_data_loader


def sample_output_data(queue):
    output_data_loader(
        "etd_1",
        "ETD",
        {
            "ResultType": "success",
            "ItemHandle": "http://example.com/handle/123123123",
            "lastModified": "Thu Sep 09 17: 56: 39 UTC 2021",
        },
        queue
    )

    output_data_loader(
        "etd_2",
        "ETD",
        {
            "ResultType": "error",
            "ErrorTimestamp": "Thu Sep 09 17: 56: 39 UTC 2021",
            "ErrorInfo": "Stuff broke",
            "ExceptionMessage": "500 Server Error: Internal Server Error",
            "ExceptionTraceback": "Full unformatted stack trace of the Exception"
        },
        queue
    )
