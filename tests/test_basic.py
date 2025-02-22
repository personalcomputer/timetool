import datetime
import pytz
from freezegun import freeze_time


# Freeze time
freezer = freeze_time(pytz.timezone("America/Los_Angeles").localize(datetime.datetime(2022, 9, 22, 16, 41, 1, 299009)))
freezer.start()


from timetool.main import run  # noqa: E402


def _test(capsys, args):
    run(args)
    return capsys.readouterr().out


def test_1(capsys):
    assert _test(capsys, ["t", "1621108906000"]) == (
        "\x1b[1m1621108906\x1b[0m\n"
        + "2021-05-15T20:01:46.000+00:00     May 15, 2021 20:01:46 UTC\n"
        + "2021-05-15T13:01:46.000-07:00     May 15, 2021 1:01:46 PM PDT\n"
        + "~1.4 years ago (42781155.299009 seconds ago)\n"
    )


def test_2(capsys):
    assert _test(capsys, ["t", "1621108906.000"]) == (
        "\x1b[1m1621108906\x1b[0m\n"
        + "2021-05-15T20:01:46.000+00:00     May 15, 2021 20:01:46 UTC\n"
        + "2021-05-15T13:01:46.000-07:00     May 15, 2021 1:01:46 PM PDT\n"
        + "~1.4 years ago (42781155.299009 seconds ago)\n"
    )


def test_3(capsys):
    assert _test(capsys, ["t", "May", "15,", "2021", "01:01:46", "PM", "PDT"]) == (
        "\x1b[1m1621108906\x1b[0m\n"
        + "2021-05-15T13:01:46.000-07:00     May 15, 2021 13:01:46 -0700\n"
        + "2021-05-15T20:01:46.000+00:00     May 15, 2021 20:01:46 UTC\n"
        + "~1.4 years ago (42781155.299009 seconds ago)\n"
    )


def test_4(capsys):
    assert _test(capsys, ["t", "2021", "May", "15th", "1:01", "PM", "GMT-0700"]) == (
        "\x1b[1m1621108860\x1b[0m\n"
        + "2021-05-15T13:01:00.000-07:00     May 15, 2021 13:01:00 -0700\n"
        + "2021-05-15T13:01:00.000-07:00     May 15, 2021 1:01:00 PM PDT\n"
        + "2021-05-15T20:01:00.000+00:00     May 15, 2021 20:01:00 UTC\n"
        + "~1.4 years ago (42781201.299009 seconds ago)\n"
    )


def test_5(capsys):
    assert _test(capsys, ["t", "2021-05-15T20:01:46.000+00:00"]) == (
        "\x1b[1m1621108906\x1b[0m\n"
        + "2021-05-15T20:01:46.000+00:00     May 15, 2021 20:01:46 UTC\n"
        + "2021-05-15T13:01:46.000-07:00     May 15, 2021 1:01:46 PM PDT\n"
        + "~1.4 years ago (42781155.299009 seconds ago)\n"
    )


def test_6(capsys):
    assert _test(capsys, ["t", "5pm", "PDT", "in", "CEST"]) == (
        "\x1b[1m1663891200\x1b[0m\n"
        + "2022-09-22T17:00:00.000-07:00     Sep 22, 2022 17:00:00 -0700\n"
        + "2022-09-23T02:00:00.000+02:00     Sep 23, 2022 2:00:00 CEST\n"
        + "2022-09-23T00:00:00.000+00:00     Sep 23, 2022 0:00:00 UTC\n"
        + "~19.0 minutes from now (1138.700991 seconds from now)\n"
    )


def test_7(capsys):
    assert _test(capsys, ["t", "now", "in", "Asia/Hong_Kong"]) == (
        "\x1b[1m1663890061\x1b[0m\n"
        + "2022-09-22T16:41:01.299-07:00     Sep 22, 2022 4:41:01 PM PDT\n"
        + "2022-09-23T07:41:01.299+08:00     Sep 23, 2022 7:41:01 AM HKT\n"
        + "2022-09-22T23:41:01.299+00:00     Sep 22, 2022 23:41:01 UTC\n"
        + "~now (0.0 seconds ago)\n"
    )


def test_8(capsys):
    assert _test(capsys, ["t", "now", "in", "IST,EDT,CEST,Asia/Tokyo"]) == (
        "\x1b[1m1663890061\x1b[0m\n"
        + "2022-09-22T16:41:01.299-07:00     Sep 22, 2022 4:41:01 PM PDT\n"
        + "2022-09-23T05:11:01.299+05:30     Sep 23, 2022 5:11:01 AM IST\n"
        + "2022-09-22T19:41:01.299-04:00     Sep 22, 2022 7:41:01 PM EDT\n"
        + "2022-09-23T01:41:01.299+02:00     Sep 23, 2022 1:41:01 CEST\n"
        + "2022-09-23T08:41:01.299+09:00     Sep 23, 2022 8:41:01 JST\n"
        + "2022-09-22T23:41:01.299+00:00     Sep 22, 2022 23:41:01 UTC\n"
        + "~now (0.0 seconds ago)\n"
    )


def test_9(capsys):
    assert _test(capsys, ["t", "-", "7d"]) == (
        "\x1b[1m1663285261\x1b[0m\n"
        + "2022-09-15T16:41:01.299-07:00     Sep 15, 2022 4:41:01 PM PDT\n"
        + "2022-09-15T23:41:01.299+00:00     Sep 15, 2022 23:41:01 UTC\n"
        + "~1.0 week ago (604800.0 seconds ago)\n"
    )


def test_10(capsys):
    assert _test(capsys, ["t", "+", "1.5h"]) == (
        "\x1b[1m1663895461\x1b[0m\n"
        + "2022-09-22T18:11:01.299-07:00     Sep 22, 2022 6:11:01 PM PDT\n"
        + "2022-09-23T01:11:01.299+00:00     Sep 23, 2022 1:11:01 UTC\n"
        + "~1.5 hours from now (5400.0 seconds from now)\n"
    )


def test_11(capsys):
    assert _test(capsys, ["t", "+", "1mo"]) == (
        "\x1b[1m1666482061\x1b[0m\n"
        + "2022-10-22T16:41:01.299-07:00     Oct 22, 2022 4:41:01 PM PDT\n"
        + "2022-10-22T23:41:01.299+00:00     Oct 22, 2022 23:41:01 UTC\n"
        + "~1.0 month from now (2592000.0 seconds from now)\n"
    )


def test_12(capsys):
    assert _test(capsys, ["t", "+1mo"]) == (
        "\x1b[1m1666482061\x1b[0m\n"
        + "2022-10-22T16:41:01.299-07:00     Oct 22, 2022 4:41:01 PM PDT\n"
        + "2022-10-22T23:41:01.299+00:00     Oct 22, 2022 23:41:01 UTC\n"
        + "~1.0 month from now (2592000.0 seconds from now)\n"
    )


def test_13(capsys):
    assert _test(capsys, ["t", "+", "01:30:00"]) == (
        "\x1b[1m1663895461\x1b[0m\n"
        + "2022-09-22T18:11:01.299-07:00     Sep 22, 2022 6:11:01 PM PDT\n"
        + "2022-09-23T01:11:01.299+00:00     Sep 23, 2022 1:11:01 UTC\n"
        + "~1.5 hours from now (5400.0 seconds from now)\n"
    )


def test_14(capsys):
    assert _test(capsys, ["t", "now"]) == (
        "\x1b[1m1663890061\x1b[0m\n"
        + "2022-09-22T16:41:01.299-07:00     Sep 22, 2022 4:41:01 PM PDT\n"
        + "2022-09-22T23:41:01.299+00:00     Sep 22, 2022 23:41:01 UTC\n"
        + "~now (0.0 seconds ago)\n"
    )
