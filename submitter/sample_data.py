from submitter.sqs import data_loader


def sample_data(input_queue, output_queue):
    data_loader(
        "123",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "466",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "789",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "asd",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "feg",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "hij",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "etd_123",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "wiley_456",
        "Wiley",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "orange",
        "ETD",
        "DSpace@MIT",
        "1721.1/131022",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
    data_loader(
        "cat",
        "popcorn",
        "devnull",
        "whatever",
        "s3:/fakeloc/a.json",
        "file 1",
        "s3:/fakeloc2/f.json",
        input_queue,
        output_queue,
    )
