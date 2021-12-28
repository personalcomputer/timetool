#!/usr/bin/env python3
import datetime
import re
import textwrap
import sys
import warnings
import csv
import importlib.resources

import pytz
import babel.dates
from babel.core import Locale, UnknownLocaleError
from babel.languages import get_territory_language_info
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as dateutil_parse
from dateutil.parser import UnknownTimezoneWarning

warnings.filterwarnings('error', category=UnknownTimezoneWarning)

# TODO: These should be set up as user configured, not hardcoded. We can hardcode some defaults, but beyond that it
# needs to be user configurable.
EXTRA_DISPLAY_ALWAYS_TIMEZONES = ['UTC']  # ['America/Los_Angeles', 'UTC']
EXTRA_TIMEZONE_ABBREVIATIONS = {
    'PACIFIC': 'America/Los_Angeles',
    'PT': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
    'MT': 'America/Denver',
    'MDT': 'America/Denver',
    'MST': 'America/Denver',
    'CT': 'America/Chicago',
    'CENTRAL': 'America/Chicago',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',  # "CST" more commonly means Asia/Shanghai... need to make this user configured.
    'ET': 'America/New_York',
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'CEST': 'Europe/Berlin',
    'CEDT': 'Europe/Berlin',
    'CET': 'Europe/Berlin',
    'IST': 'Asia/Kolkata',
    'BST': 'Europe/London',
}

# Note: timeconv tries to correctly format times partially using locale information of the locale(s) using that
# timezone. One timezone is often used by many locales, but there is still a single most likely locale for each
# timezone. tzinfo used to provide a single primary "country" per timezone, so we use that deprecated data for our
# purposes. This info is not exposed by python zoneinfo, so we need to have our own zoneinfo file parser. For
# (attempted) Windows compatibility, we load it in from the tzdata package instead of using the os-provided zoneinfo.
zone_tab = csv.reader(importlib.resources.open_text('tzdata.zoneinfo', 'zone.tab'), delimiter='\t')
tz_to_country_str = {
    tz[2]: tz[0].upper() for tz in zone_tab if len(tz) >= 3
}


def format_datetime_for_inferred_locale(time, with_seconds=True, date_fmt='long'):
    fmt_sec = ':%S' if with_seconds else ''
    if date_fmt == 'long':
        fmt_date = '%b %d, %Y '
    elif date_fmt == 'short':
        fmt_date = '%b %d '
    elif date_fmt is None:
        fmt_date = ''
    else:
        raise KeyError

    zone_key = None
    if hasattr(time.tzinfo, 'zone'):
        # Handle pytz-style timezones
        zone_key = time.tzinfo.zone
    elif hasattr(time.tzinfo, 'key'):
        # Handle zoneinfo-style timezones
        zone_key = time.tzinfo.key
    else:
        # Timezone is an offset-only
        if time.tzinfo.utcoffset(time).total_seconds() == 0:
            # If offset-only and the offset is zero - 99% of the time people mean UTC, so force it into being UTC and
            # handle as UTC.
            time = time.astimezone(pytz.UTC)
            zone_key = time.tzinfo.zone
        else:
            zone_key = None

    # Render with tz represented as an offset when TZ is unidentified.
    if not zone_key:
        return time.strftime(f'{fmt_date}%-H:%M{fmt_sec} %z')
    # Render as 24hr clock if utc.
    if zone_key == 'UTC':
        return time.strftime(f'{fmt_date}%-H:%M{fmt_sec} %Z')
    # Render as 12hr clock if the timezone's primary locale uses 12 hr clock.
    try:
        country = tz_to_country_str[zone_key]
        lang = list(get_territory_language_info(country).keys())[0]
        locale = Locale.parse(f'{lang}_{country}')
    except (UnknownLocaleError, KeyError):
        pass
    else:
        if 'a' in str(locale.time_formats['long']):  # pylint: disable=R1705
            if date_fmt == 'long':
                return time.strftime(f'{fmt_date}%-I:%M{fmt_sec} %p %Z')
            ampm = time.strftime('%p').lower()[0]
            return time.strftime(f'{fmt_date}%-I:%M{fmt_sec}{ampm} %Z')
    # Render as 24hr clock otherwise.
    return time.strftime(f'{fmt_date}%-H:%M{fmt_sec} %Z')


def parse_timezone(input_timezone_raw):
    if not input_timezone_raw:
        return None
    if input_timezone_raw.strip().lower() in ('local', 'localtz', 'tzlocal', 'localzone'):
        return babel.dates.LOCALTZ
    if input_timezone_raw.upper() in EXTRA_TIMEZONE_ABBREVIATIONS:
        # Adjust the user input into a real tzinfo, if a mapping is known.
        input_timezone_raw = EXTRA_TIMEZONE_ABBREVIATIONS[input_timezone_raw.upper()]
    return pytz.timezone(input_timezone_raw)


def parse_datetime(datetime_agg):
    class Ret:
        def __init__(self):
            self.input_time = None
            self.input_timezone_raw = None
            self.highlight_input_time = False
            self.display_timezones = []

    ret = Ret()

    # Check if the time used 'X in <TIMEZONE>' pattern, if so ensure we display that timezone in the output
    match = re.search(r' (?:as|in) ((?:[a-zA-Z/_]{2,},? ?){1,})$', datetime_agg, re.IGNORECASE)
    if match:
        ret.display_timezones = [parse_timezone(item.strip()) for item in match.group(1).split(',')]
        datetime_agg = datetime_agg[:match.span()[0]]

    # Check if the time is 'now', or entirely empty.
    if datetime_agg.strip().lower() in ('', 'now', 'current', 'today'):
        ret.input_time = datetime.datetime.now(tz=babel.dates.LOCALTZ)
        return ret

    # Maybe it is a relative time, in form e.g. "-7day"?
    ALL_UNITS = ('y', 'year', 'years', 'mo', 'month', 'months', 'wk', 'w', 'week', 'weeks', 'd', 'day', 'days', 'h',
                 'hour', 'hours', 'm', 'min', 'mins', 'minute', 'minutes', 's', 'sec', 'secs', 'seconds',)
    UNITS_REGEX = '|'.join(ALL_UNITS)
    match = re.match(r'^(?P<sign>[-+])(?P<value>\d{1,8}(?:\.\d+)?) ?(?P<unit>' + UNITS_REGEX + ')', datetime_agg,
                     re.IGNORECASE)
    if match:
        value = float(match.group('value'))
        if match.group('sign') == '-':
            value *= -1
        unit = match.group('unit').lower()
        if unit in ('y', 'year', 'years'):
            delta = relativedelta(years=value)
        elif unit in ('mo', 'month', 'months'):
            delta = relativedelta(months=value)
        elif unit in ('wk', 'w', 'week', 'weeks'):
            delta = relativedelta(weeks=value)
        elif unit in ('d', 'day', 'days'):
            delta = relativedelta(days=value)
        elif unit in ('h', 'hour', 'hours'):
            delta = relativedelta(hours=value)
        elif unit in ('m', 'min', 'mins', 'minute', 'minutes'):
            delta = relativedelta(minutes=value)
        elif unit in ('s', 'sec', 'secs', 'seconds'):
            delta = relativedelta(seconds=value)
        now = datetime.datetime.now(tz=babel.dates.LOCALTZ)
        ret.input_time = now + delta
        return ret

    # Maybe it is a relative time, in form e.g. "-01:30:"?
    match = re.match(r'^(?P<sign>[-+])(?P<hours>\d{0,2}):(?P<minutes>\d{0,2}):(?P<seconds>\d{0,2})', datetime_agg,
                     re.IGNORECASE)
    if match:
        delta = datetime.timedelta(seconds=sum([
            (float(match.group('hours'))   if match.group('hours')   else 0) * 60 * 60, # noqa E272
            (float(match.group('minutes')) if match.group('minutes') else 0) * 60,
            (float(match.group('seconds')) if match.group('seconds') else 0)
        ]))
        if match.group('sign') == '-':
            delta *= -1
        now = datetime.datetime.now(tz=babel.dates.LOCALTZ)
        ret.input_time = now + delta
        return ret

    # Maybe it is unix time?
    if re.match(r'^\d{9,12}(?:\.\d+)?$', datetime_agg):
        ret.input_time = pytz.utc.localize(datetime.datetime.utcfromtimestamp(float(datetime_agg)))
        return ret

    # Or unixtime with milliseconds?
    if re.match(r'^\d{13,16}$', datetime_agg):
        ret.input_time = pytz.utc.localize(datetime.datetime.utcfromtimestamp(int(datetime_agg) / 1000.0))
        return ret

    # Try parsing with dateutil - this is the main mode
    try:
        # First convert specifications like GMT+6 or UTC+6 into just "+6" to avoid the counter-intuitive and unusual
        # design behavior of dateutil to interpret UTC+6 as meaning a timezone with UTC offset of -0600, which is
        # opposite to the expected interpretation of it meaning UTC offset +0600. More details at
        # https://github.com/dateutil/dateutil/issues/70
        datetime_agg_massaged = re.sub(r'(?:GMT|UTC)([+\-]\d+)', r'\1', datetime_agg)

        ret.input_time = dateutil_parse(datetime_agg_massaged)
        return ret
    except (ValueError, UnknownTimezoneWarning) as exc:
        original_exception = exc

    # Maybe the timezone was included?
    try:
        input_time_raw = datetime_agg.rsplit(' ', 1)[0]
        ret.input_time = dateutil_parse(input_time_raw)
        ret.input_timezone_raw = datetime_agg.rsplit(' ', 1)[1]
        return ret
    except ValueError:
        pass

    # Maybe it is actually JUST a timezone they entered?
    try:
        timezone = parse_timezone(datetime_agg)
    except pytz.exceptions.UnknownTimeZoneError:
        pass
    else:
        if timezone:
            ret.input_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(timezone)
            if not ret.display_timezones:
                ret.highlight_input_time = True
            return ret

    raise original_exception


def main():
    USAGE = textwrap.dedent('''
        Usage: {prog} [-h] [TIME] [in CONVERSION_TIMEZONE]

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
          {prog} -7d
          {prog} +1.5h
          {prog} +1mo
          {prog} +01:30:00

        Help & support:
          https://github.com/personalcomputer/timetool/issues
    ''').strip()
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print(USAGE.format(prog=sys.argv[0]))
        return

    datetime_agg = ' '.join([arg.strip() for arg in sys.argv[1:]])
    if datetime_agg.endswith('-l'):
        datetime_agg = datetime_agg[:-2].strip()
        oneline = True
    else:
        oneline = False
    input_time = None
    input_timezone_raw = None
    highlight_input_time = False

    try:
        ret = parse_datetime(datetime_agg)
        input_time, input_timezone_raw, highlight_input_time, extra_display_timezones = \
            ret.input_time, ret.input_timezone_raw, ret.highlight_input_time, ret.display_timezones
    except ValueError as exc:
        print(*exc.args)
        sys.exit(1)

    # Add Timezone (if specified in two parts)
    if input_time.tzinfo is None:
        if not input_timezone_raw:
            print('Error: Ambiguous timezone in input. Please use a datetime format that encodes a timezone (e.g. '
                  'iso8601 strings or unixtimes), or explicitly specify an a timezone after.')
            sys.exit(1)
        input_timezone = parse_timezone(input_timezone_raw)
        if hasattr(input_timezone, 'localize'):
            input_time = input_timezone.localize(input_time)
        else:
            input_time = input_time.replace(tzinfo=input_timezone)
    elif input_timezone_raw:
        print('Error: Multiple input timezones provided. Note that some input formats encode a timezone already (e.g. '
              'iso8601 strings or unixtimes).')
        sys.exit(1)

    # Convert
    utc_time = input_time.astimezone(pytz.utc)
    unix_time = input_time.timestamp()
    assert unix_time == (utc_time - pytz.utc.localize(datetime.datetime.utcfromtimestamp(0))).total_seconds()

    # Output
    prefix = '\033[1m' if not highlight_input_time else ''
    print(f'{prefix}{unix_time:.0f}\033[0m')

    display_timezones = [
        input_time.tzinfo,
        babel.dates.LOCALTZ,
    ] + extra_display_timezones + [
        pytz.timezone(tzstr) for tzstr in EXTRA_DISPLAY_ALWAYS_TIMEZONES
    ]

    display_times = []

    seen_timezone_fingerprints = set([])
    for tz in display_timezones:
        time = utc_time.astimezone(tz)
        tz_fingerprint = (time.tzname(), time.utcoffset())
        if tz_fingerprint in seen_timezone_fingerprints:
            continue
        seen_timezone_fingerprints.add(tz_fingerprint)
        display_times.append(time)

    for time in display_times:
        print(''.join((
            time.isoformat(timespec='milliseconds'),
            '     ',
            format_datetime_for_inferred_locale(time),
        )))

    oneline = True
    if oneline:
        has_shared_date = True
        shared_date = None
        for time in display_times:
            if not shared_date:
                shared_date = time.date()
            elif time.date() != shared_date:
                has_shared_date = False
                break

        with_seconds = utc_time.second != 0  # or utc_time.microsecond != 0
        time_str = format_datetime_for_inferred_locale(
            display_times[0], date_fmt='long', with_seconds=with_seconds
        )

        date_fmt = None if has_shared_date else 'short'
        time_strs = [
            format_datetime_for_inferred_locale(
                time, date_fmt=date_fmt, with_seconds=with_seconds
            ) for time in display_times[1:]
        ]
        if time_strs:
            time_str += f' ({" / ".join(time_strs)})'
        print(time_str)


if __name__ == "__main__":
    main()
