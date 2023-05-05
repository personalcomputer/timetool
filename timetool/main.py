#!/usr/bin/env python3
import csv
import datetime
import importlib.resources
import re
import sys
import textwrap
import warnings
from math import floor
from operator import add
from operator import sub as subtract

import babel.dates
import pytz
from babel.core import Locale, UnknownLocaleError
from babel.languages import get_territory_language_info
from dateutil.parser import UnknownTimezoneWarning
from dateutil.parser import parse as dateutil_parse
from dateutil.relativedelta import relativedelta

warnings.filterwarnings("error", category=UnknownTimezoneWarning)

# TODO: These should be set up as user configured, not hardcoded. We can hardcode some defaults, but beyond that it
# needs to be user configurable.
EXTRA_DISPLAY_ALWAYS_TIMEZONES = ["UTC"]  # ['America/Los_Angeles', 'UTC']
EXTRA_TIMEZONE_ABBREVIATIONS = {
    "PACIFIC": "America/Los_Angeles",
    "PT": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "MOUNTAIN": "America/Denver",
    "MT": "America/Denver",
    "MDT": "America/Denver",
    "MST": "America/Denver",
    "CENTRAL": "America/Chicago",
    "CT": "America/Chicago",
    "CDT": "America/Chicago",
    "CST": "America/Chicago",  # "CST" more commonly means Asia/Shanghai... need to make this user configured.
    "EASTERN": "America/New_York",
    "ET": "America/New_York",
    "EDT": "America/New_York",
    "EST": "America/New_York",
    "BST": "Europe/London",
    "CET": "Europe/Berlin",
    "CEST": "Europe/Berlin",
    "CEDT": "Europe/Berlin",
    "IST": "Asia/Kolkata",
}

# Note: timeconv tries to correctly format times partially using locale information of the locale(s) using that
# timezone. One timezone is often used by many locales, but there is still a single most likely locale for each
# timezone. tzinfo used to provide a single primary "country" per timezone, so we use that deprecated data for our
# purposes. This info is not exposed by python zoneinfo, so we need to have our own zoneinfo file parser. For
# (attempted) Windows compatibility, we load it in from the tzdata package instead of using the os-provided zoneinfo.
zone_tab = csv.reader(importlib.resources.open_text("tzdata.zoneinfo", "zone.tab"), delimiter="\t")
tz_to_country_str = {tz[2]: tz[0].upper() for tz in zone_tab if len(tz) >= 3}

now = datetime.datetime.now(tz=babel.dates.LOCALTZ)


def format_datetime_for_inferred_locale(time, with_seconds=True, date_fmt="long"):
    fmt_sec = ":%S" if with_seconds else ""
    if date_fmt == "long":
        fmt_date = "%b %d, %Y "
    elif date_fmt == "short":
        fmt_date = "%b %d "
    elif date_fmt is None:
        fmt_date = ""
    else:
        raise KeyError

    zone_key = None
    if hasattr(time.tzinfo, "zone"):
        # Handle pytz-style timezones
        zone_key = time.tzinfo.zone
    elif hasattr(time.tzinfo, "key"):
        # Handle zoneinfo-style timezones
        zone_key = time.tzinfo.key
    else:
        # Timezone is an offset-only
        if time.tzinfo.utcoffset(time).total_seconds() == 0:
            # If offset-only and the offset is zero then 99% of the time people mean UTC, so force it into being UTC and
            # handle as UTC.
            # (the other 1% of the time they mean GMT instead, i.e. Europe/Lonodon)
            time = time.astimezone(pytz.UTC)
            zone_key = time.tzinfo.zone
        else:
            zone_key = None

    # Render with tz represented as an offset when TZ is unidentified.
    if not zone_key:
        return time.strftime(f"{fmt_date}%-H:%M{fmt_sec} %z")
    # Render as 24hr clock if utc.
    if zone_key == "UTC":
        return time.strftime(f"{fmt_date}%-H:%M{fmt_sec} %Z")
    # Render as 12hr clock if the timezone's primary locale uses 12 hr clock.
    try:
        country = tz_to_country_str[zone_key]
        lang = list(get_territory_language_info(country).keys())[0]
        locale = Locale.parse(f"{lang}_{country}")
    except (UnknownLocaleError, KeyError):
        pass
    else:
        if "a" in str(locale.time_formats["long"]):  # pylint: disable=R1705
            if date_fmt == "long":
                return time.strftime(f"{fmt_date}%-I:%M{fmt_sec} %p %Z")
            ampm = time.strftime("%p").lower()[0]
            return time.strftime(f"{fmt_date}%-I:%M{fmt_sec}{ampm} %Z")
    # Render as 24hr clock otherwise.
    return time.strftime(f"{fmt_date}%-H:%M{fmt_sec} %Z")


def parse_timezone(input_timezone_raw):
    if not input_timezone_raw:
        return None
    if input_timezone_raw.strip().lower() in ("local", "localtz", "tzlocal", "localzone"):
        return babel.dates.LOCALTZ
    if input_timezone_raw.upper() in EXTRA_TIMEZONE_ABBREVIATIONS:
        # Adjust the user input into a real tzinfo, if a mapping is known.
        input_timezone_raw = EXTRA_TIMEZONE_ABBREVIATIONS[input_timezone_raw.upper()]
    return pytz.timezone(input_timezone_raw)


def parse_delta_time(input_str):
    # Format e.g. "-7day"
    ALL_UNITS = (
        "y",
        "yr",
        "yrs",
        "year",
        "years",
        "mo",
        "month",
        "months",
        "w",
        "wk",
        "week",
        "weeks",
        "d",
        "day",
        "days",
        "h",
        "hr",
        "hrs",
        "hour",
        "hours",
        "m",
        "min",
        "mins",
        "minute",
        "minutes",
        "s",
        "sec",
        "secs",
        "seconds",
        "ms",
        "millisecond",
        "milliseconds",
    )
    UNITS_REGEX = "|".join(ALL_UNITS)
    match = re.match(
        r"^(?P<sign>[-+]) ?(?P<value>\d{1,8}(?:\.\d+)?) ?(?P<unit>" + UNITS_REGEX + r")(?:\s|$)",
        input_str,
        re.IGNORECASE,
    )
    if match:
        value = float(match.group("value"))
        if match.group("sign") == "-":
            value *= -1
        unit = match.group("unit").lower()
        if unit in ("y", "yr", "yrs", "year", "years"):
            fraction = value % 1
            delta = relativedelta(years=int(floor(value)))
            delta += relativedelta(
                days=fraction * 365
            )  # (approx) It's not possible to perfectly support fractional years
        elif unit in ("mo", "month", "months"):
            fraction = value % 1
            delta = relativedelta(months=int(floor(value)))
            delta += relativedelta(
                days=fraction * 30.417
            )  # (approx) It's not possible to perfectly support fractional months
        elif unit in ("w", "wk", "week", "weeks"):
            delta = relativedelta(weeks=value)
        elif unit in ("d", "day", "days"):
            delta = relativedelta(days=value)
        elif unit in ("h", "hr", "hrs", "hour", "hours"):
            delta = relativedelta(hours=value)
        elif unit in ("m", "min", "mins", "minute", "minutes"):
            delta = relativedelta(minutes=value)
        elif unit in ("s", "sec", "secs", "seconds"):
            delta = relativedelta(seconds=value)
        elif unit in ("ms", "millisecond", "milliseconds"):
            delta = relativedelta(seconds=value / 1000)
        return delta

    # Format e.g. "-01:30:"
    match = re.match(
        r"^(?P<sign>[-+]) ?(?P<hours>\d{0,2}):(?P<minutes>\d{0,2}):(?P<seconds>\d{0,2})(?:\s|$)",
        input_str,
        re.IGNORECASE,
    )
    if match:
        delta = datetime.timedelta(
            seconds=sum(
                [
                    (float(match.group("hours")) if match.group("hours") else 0) * 60 * 60,
                    (float(match.group("minutes")) if match.group("minutes") else 0) * 60,
                    (float(match.group("seconds")) if match.group("seconds") else 0),
                ]
            )
        )
        if match.group("sign") == "-":
            delta *= -1
        return delta

    return None


def parse_datetime_core(datetime_agg, log_input_format=False):
    def log_format(format_str):
        if log_input_format:
            print(f"Input parsed using format: {format_str}")

    input_timezone_raw = None
    stripped_dt_agg = datetime_agg.strip().lower()

    # Check if the time is "now" (including the behavior for entirely empty input)
    if stripped_dt_agg in ("now", "current", "currently", "today", "current time", "local time"):
        log_format("now prose")
        return now, input_timezone_raw
    if stripped_dt_agg == "":
        log_format("blank")
        return now, input_timezone_raw

    # Maybe it is a relative time, in form e.g. "-7day"?
    delta = parse_delta_time(datetime_agg)
    if delta is not None:
        log_format("relative time specifer")
        return now + delta, input_timezone_raw

    # Maybe it is a relative time, in form e.g. "tomorrow"?
    if stripped_dt_agg in ("tomorrow", "yesterday"):
        log_format("relative time prose")
        if stripped_dt_agg == "tomorrow":
            return now + relativedelta(days=1), input_timezone_raw
        if stripped_dt_agg == "yesterday":
            return now + relativedelta(days=-1), input_timezone_raw

    DAYS_OF_WEEK = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    dow_match = re.match(r"(next|last) (" + ("|".join(DAYS_OF_WEEK)) + ")", stripped_dt_agg.lower())
    if dow_match:
        log_format("relative time prose")
        ret_time = now
        if dow_match.group(1) == "last":
            ret_time += relativedelta(weeks=-1)
        else:
            assert dow_match.group(1) == "next"
            # Add one day first, because otherwise if you do "next monday" and it is currently monday, it will just
            # pick today.
            ret_time += relativedelta(days=1)
        ret_time += relativedelta(weekday=DAYS_OF_WEEK.index(dow_match.group(2)))
        return ret_time, input_timezone_raw

    # Maybe it is unix time?
    # Warning: Without leading zeros, our logic only supports unix times after **1973-03-03** and up to **33658**
    if re.match(r"^\d{9,12}(?:\.\d+)?$", datetime_agg):
        log_format("unix")
        return datetime.datetime.fromtimestamp(float(datetime_agg), tz=datetime.timezone.utc), input_timezone_raw
    # Or unixime with milliseconds?
    # Warning: Without leading zeros, our logic only supports unix times w/ ms after **2001-09-09** and up to **33658**
    if re.match(r"^\d{13,15}$", datetime_agg):
        log_format("unix milliseconds")
        return datetime.datetime.fromtimestamp(int(datetime_agg) / 1000.0, tz=datetime.timezone.utc), input_timezone_raw
    # Or unixtime with microseconds?
    # Warning: Without leading zeros, our logic only supports unix times w/ us after **1973-03-03** and up to **5138**
    if re.match(r"^\d{16,18}$", datetime_agg):
        log_format("unix microseconds")
        return datetime.datetime.fromtimestamp(int(datetime_agg) / 10000000.0, tz=datetime.timezone.utc), input_timezone_raw
    # Or unixtime with nanoseconds?
    # Warning: Without leading zeros, our logic only supports unix times w/ ns after **2001-09-09** and up to **33658**
    if re.match(r"^\d{19,21}$", datetime_agg):
        log_format("unix nanoseconds")
        return (
            datetime.datetime.fromtimestamp(int(datetime_agg) / 1000000000.0, tz=datetime.timezone.utc),
            input_timezone_raw,
        )

    # Try parsing with dateutil - this is the main mode
    try:
        # First convert specifications like GMT+6 or UTC+6 into just "+6" to avoid the extremely counter-intuitive and
        # unusual design behavior of dateutil/POSIX. POSIX specifies to interpret UTC+6 as meaning a timezone with UTC
        # offset of -0600, which is opposite to the expected interpretation of it meaning UTC offset +0600. More
        # details at https://github.com/dateutil/dateutil/issues/70
        datetime_agg_massaged = re.sub(r"(?:GMT|UTC)([+\-]\d+)", r"\1", datetime_agg)
        ret = dateutil_parse(datetime_agg_massaged), input_timezone_raw
        # todo: try passing in EXTRA_TIMEZONE_ABBREVIATIONS as `tzinfos` arg to dateutil_parse.
        log_format("dateutil (unknown)")
        return ret
    except (ValueError, UnknownTimezoneWarning) as exc:
        original_exception = exc

    # Maybe an unrecognized timezone was included?
    try:
        input_time_raw = datetime_agg.rsplit(" ", 1)[0]
        input_timezone_raw = datetime_agg.rsplit(" ", 1)[1]
        log_format("dateutil (unknown) with extra timezone")
        return dateutil_parse(input_time_raw), input_timezone_raw
    except (ValueError, IndexError):
        pass

    # Maybe it is actually JUST a timezone they entered?
    try:
        timezone = parse_timezone(datetime_agg)
    except pytz.exceptions.UnknownTimeZoneError:
        pass
    else:
        if timezone:
            log_format("solo timezone")
            return now.astimezone(timezone), input_timezone_raw

    raise original_exception


def add_timezone(input_time, input_timezone_raw):
    if input_time.tzinfo is None:
        if not input_timezone_raw:
            raise ValueError(
                "Ambiguous timezone in input. Please use a datetime format that encodes a timezone (e.g. "
                + "iso8601 strings or unixtimes), or explicitly specify a timezone after."
            )
        input_timezone = parse_timezone(input_timezone_raw)
        if hasattr(input_timezone, "localize"):
            return input_timezone.localize(input_time)
        else:
            return input_time.replace(tzinfo=input_timezone)
    elif input_timezone_raw:
        raise ValueError(
            "Multiple input timezones provided. Note that some input formats encode a timezone already (e.g. "
            + "iso8601 strings or unixtimes)."
        )
    return input_time


def parse_datetime(datetime_agg, log_input_format=False):
    input_time, input_timezone_raw = parse_datetime_core(datetime_agg, log_input_format)
    input_time = add_timezone(input_time, input_timezone_raw)
    return input_time


def qnr(a, b):
    """Return quotient and remainder"""
    return a / b, a % b


def humanize_oneterm_timedelta(delta: datetime.timedelta):
    """Inspired by https://gist.github.com/zhangsen/1199964"""
    day_raw = delta.total_seconds() / (24 * 60 * 60)
    second_raw = delta.seconds
    microsecond_raw = delta.microseconds
    year, day = qnr(day_raw, 365)
    month, day = qnr(day, 30.417)
    week, day = qnr(day, 7)
    hour, second = qnr(second_raw, 3600)
    minute, second = qnr(second, 60)
    millisecond, microsecond = qnr(microsecond_raw, 1000)
    periods_zipped = [
        ("year", year),
        ("month", month),
        ("week", week),
        ("day", day),
        ("hour", hour),
        ("minute", minute),
        ("second", second),
        ("millisecond", millisecond),
        ("microsecond", microsecond),
    ]
    for period_name, value in periods_zipped:
        if value < 1:
            continue
        plural = "" if value == 1 else "s"
        return f"{round(value, 1):.1f} {period_name}{plural}"


def humanize_oneterm_relativedelta(delta: relativedelta):
    delta = delta.normalized()
    if delta.microseconds < 0:
        delta.seconds -= 1
        delta.microseconds = 1000000 + delta.microseconds
    delta.seconds += delta.microseconds / 1000000
    delta.minutes += delta.seconds / 60
    delta.hours += delta.minutes / 60
    delta.days += delta.hours / 24
    delta.months += delta.days / 30.417
    delta.years += delta.months / 12

    milliseconds, delta.microseconds = qnr(delta.microseconds, 1000)
    weeks, delta.days = qnr(delta.days, 7)

    periods_zipped = [
        ("year", delta.years),
        ("month", delta.months),
        ("week", weeks),
        ("day", delta.days),
        ("hour", delta.hours),
        ("minute", delta.minutes),
        ("second", delta.seconds),
        ("millisecond", milliseconds),
        ("microsecond", delta.microseconds),
    ]
    for period_name, value in periods_zipped:
        if value < 1:
            continue
        plural = "s" if value > 1 else ""
        display_value = round(value, 1)
        return f"{display_value} {period_name}{plural}"
    return "identical"


def humanize_multiterm(delta: relativedelta, precise=False):
    delta = delta.normalized()
    if delta.microseconds < 0:
        delta.seconds -= 1
        delta.microseconds = 1000000 + delta.microseconds
    output = []
    periods_zipped = [
        ("year", delta.years),
        ("month", delta.months),
        ("week", delta.days // 7),
        ("day", delta.days % 7),
        ("hour", delta.hours),
        ("minute", delta.minutes),
        ("second", delta.seconds),
        ("microsecond", delta.microseconds),
    ]
    for period_name, value in periods_zipped:
        if value < 1:
            if output and not precise:
                break
            continue
        plural = "" if value == 1 else "s"
        output.append(f"{value} {period_name}{plural}")
        if len(output) >= 2 and not precise:
            break
    if not output:
        return "identical"
    return " and ".join(output)


def humanize_seconds(delta: datetime.timedelta):
    value = delta.total_seconds()
    plural = "" if value == 1 else "s"
    return f"{value} second{plural}"


def humanize_time_difference(a_dt, b_dt, variant, relative_to_now_prose=False):
    delta = a_dt - b_dt
    delta_seconds = delta.total_seconds()
    rel_delta = relativedelta(a_dt, b_dt)
    relative_term = ""
    sign = ""
    if delta_seconds < 0:
        rel_delta *= -1
        delta *= -1
        if relative_to_now_prose:
            relative_term = " from now"
        else:
            sign = "-"
    else:
        if relative_to_now_prose:
            relative_term = " ago"
        else:
            sign = ""

    if variant == "multiterm":
        delta_str = humanize_multiterm(rel_delta)
    elif variant == "multiterm-precise":
        delta_str = humanize_multiterm(rel_delta, precise=True)
    elif variant == "oneterm":
        delta_str = humanize_oneterm_relativedelta(rel_delta)
    elif variant == "oneterm-alt":
        delta_str = humanize_oneterm_timedelta(delta)
    elif variant == "seconds":
        delta_str = humanize_seconds(delta)

    if delta_str in ("within a second", "identical") and relative_to_now_prose:
        # provide a more now-related casual statement for times very close to now
        return "now"
    else:
        return f"{sign}{delta_str}{relative_term}"
    return delta_str


def run(argv):
    USAGE = textwrap.dedent(
        """
        Usage: {prog} [-h] [TIME] [in CONVERSION_TIMEZONE] [-o][-e][-i]

        Flags:
            -o  Show "one line" output format that includes all timezones in one line.
            -e  Show extended delta time formats.
            -i  Output JUST an ISO8601 UTC time. For repurposing timetool for use in scripts.

        Examples:
          {prog}
          {prog} 1621108906
          {prog} 1621108906000
          {prog} 1621108906.000
          {prog} May 15, 2021 01:01:46 PM PDT
          {prog} 2021 May 15th 1:01 PM GMT-0700
          {prog} 2021-05-15T20:01:46.000+00:00
          {prog} 5pm PDT in CEST
          {prog} now in Asia/Hong_Kong
          {prog} now in IST,EDT,CEST,Asia/Tokyo
          {prog} - 7d
          {prog} + 1.5h
          {prog} + 1mo
          {prog} + 01:30:00

        Help & support:
          https://github.com/personalcomputer/timetool/issues
    """
    ).strip()
    if len(argv) > 1 and (set(argv) & set(["-h", "--help"])):
        print(USAGE.format(prog=argv[0]))
        return

    if "--debug" in argv:
        argv.remove("--debug")
        debug = True
    else:
        debug = False
    if "-e" in argv:
        argv.remove("-e")
        extra_output = True
    else:
        extra_output = False
    if "-o" in argv:
        argv.remove("-o")
        oneline = True
    else:
        oneline = False
    if "-i" in argv:
        argv.remove("-i")
        iso8601_only_mode = True
    else:
        iso8601_only_mode = False
    datetime_agg = " ".join([arg.strip() for arg in argv[1:]])

    # Check if the time used 'X in <TIMEZONE>' pattern, and if so then ensure we display that timezone in the output
    match = re.search(r" (?:as|in) ((?:[a-zA-Z/_]{2,},? ?){1,})$", datetime_agg, re.IGNORECASE)
    if match:
        extra_display_timezones = [parse_timezone(item.strip()) for item in match.group(1).split(",")]
        datetime_agg = datetime_agg[: match.span()[0]]
    else:
        extra_display_timezones = []

    display_prefix = ""

    if " - " in datetime_agg or " + " in datetime_agg:
        # Time arithmetic!
        if " - " in datetime_agg:
            operator_char = "-"
            operator = subtract
        elif " + " in datetime_agg:
            operator_char = "+"
            operator = add
        else:
            raise AssertionError
        a_str, b_str = datetime_agg.split(f" {operator_char} ")
        a_dt = parse_datetime(a_str)
        try:
            b_dt = parse_datetime(b_str)
            finding_delta = True
        except (ValueError, pytz.exceptions.UnknownTimeZoneError) as exc:
            b_delta = parse_delta_time(f"{operator_char} {b_str}")  # try for delta time
            if not b_delta:
                raise exc
            finding_delta = False
        if finding_delta:
            if operator == add:
                print("Error: Cannot add two datetimes together")
                sys.exit(1)
            if not iso8601_only_mode:
                print(
                    f"{format_datetime_for_inferred_locale(a_dt)} {operator_char} {format_datetime_for_inferred_locale(b_dt)}"
                )
            handle_delta_display(a_dt, b_dt, extra_output=extra_output)
            return
        # finding absolute..
        if not iso8601_only_mode:
            print(f"{format_datetime_for_inferred_locale(a_dt)} {operator_char} {b_str}")
        input_time = a_dt + b_delta
        display_prefix = "= "
    else:
        # Just a single time!
        try:
            input_time = parse_datetime(datetime_agg, log_input_format=extra_output)
        except ValueError as exc:
            if debug:
                raise
            print("Error: " + (" ".join(exc.args)))
            sys.exit(1)

    handle_time_display(
        input_time,
        display_prefix=display_prefix,
        oneline=oneline,
        iso8601_only_mode=iso8601_only_mode,
        extra_output=extra_output,
        extra_display_timezones=extra_display_timezones,
    )


def handle_delta_display(a_dt, b_dt, extra_output):
    output = [
        f'~{humanize_time_difference(a_dt, b_dt, variant="oneterm")} '
        + f'({humanize_time_difference(a_dt, b_dt, variant="seconds")})'
    ]
    if extra_output:
        output.extend(
            [
                humanize_time_difference(a_dt, b_dt, variant="multiterm-precise"),
                "~" + humanize_time_difference(a_dt, b_dt, variant="multiterm"),
                "~" + humanize_time_difference(a_dt, b_dt, variant="oneterm-alt"),
            ]
        )
    print(textwrap.indent("\n".join(output), "= "))


def handle_time_display(input_time, display_prefix, oneline, iso8601_only_mode, extra_output, extra_display_timezones):
    utc_time = input_time.astimezone(pytz.utc)

    if iso8601_only_mode:
        print(utc_time.isoformat(timespec="milliseconds"))
        return

    # Unix
    unix_time = input_time.timestamp()
    assert unix_time == (utc_time - pytz.utc.localize(datetime.datetime.utcfromtimestamp(0))).total_seconds()
    output = []
    BOLD_TERM_CODE = "\033[1m"  # TODO: Use tput (actually, curses - tigetstr('bold') & tigetstr('sgr0'))
    NOBOLD_TERM_CODE = "\033[0m"
    output.append(f"{BOLD_TERM_CODE}{unix_time:.0f}{NOBOLD_TERM_CODE}")

    # Main display of two formats for each timezone
    display_timezones = (
        [
            input_time.tzinfo,
            babel.dates.LOCALTZ,
        ]
        + extra_display_timezones
        + [pytz.timezone(tzstr) for tzstr in EXTRA_DISPLAY_ALWAYS_TIMEZONES]
    )

    display_times = []
    seen_timezone_fingerprints = set()
    for tz in display_timezones:
        time = utc_time.astimezone(tz)
        tz_fingerprint = (time.tzname(), time.utcoffset())
        if tz_fingerprint in seen_timezone_fingerprints:
            continue
        seen_timezone_fingerprints.add(tz_fingerprint)
        display_times.append(time)
    for time in display_times:
        output.append(
            "".join(
                (
                    time.isoformat(timespec="milliseconds"),
                    "     ",
                    format_datetime_for_inferred_locale(time),
                )
            )
        )

    # Extra display
    if extra_output or oneline:
        has_shared_date = True
        shared_date = None
        for time in display_times:
            if not shared_date:
                shared_date = time.date()
            elif time.date() != shared_date:
                has_shared_date = False
                break

        with_seconds = utc_time.second != 0  # or utc_time.microsecond != 0
        time_str = format_datetime_for_inferred_locale(display_times[0], date_fmt="long", with_seconds=with_seconds)

        date_fmt = None if has_shared_date else "short"
        time_strs = [
            format_datetime_for_inferred_locale(time, date_fmt=date_fmt, with_seconds=with_seconds)
            for time in display_times[1:]
        ]
        if time_strs:
            time_str += f' ({" / ".join(time_strs)})'
        output.append(time_str)

    output.extend(
        [
            f'~{humanize_time_difference(now, time, variant="oneterm", relative_to_now_prose=True)} '
            + f'({humanize_time_difference(now, time, variant="seconds", relative_to_now_prose=True)})'
        ]
    )
    if extra_output:
        output.extend(
            [
                humanize_time_difference(now, time, variant="multiterm-precise", relative_to_now_prose=True),
                "~" + humanize_time_difference(now, time, variant="oneterm-alt", relative_to_now_prose=True),
                "~" + humanize_time_difference(now, time, variant="multiterm", relative_to_now_prose=True),
            ]
        )
    output_str = "\n".join(output)
    if display_prefix:
        output_str = textwrap.indent(output_str, display_prefix)
    print(output_str)


def main():
    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
