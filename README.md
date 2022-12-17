# timetool (`t`)

timetool, or `t`, is a little command line utility for you to convert between different timezones and datetime
formats.

It accepts a time as input, in any format, and then outputs it in many different formats and timezones at once.

timetool is not meant to used in scripts, it was just created to be a better & faster alternative to commonly used web
tools like https://www.epochconverter.com/ and https://www.timeanddate.com/worldclock/converter.html.

## Install

```sh
pip install timetool

# Alias timetool as t. This is optional, but recommended for fast access.
alias t=timetool
echo 'alias t=timetool' >> ~/.bashrc
echo 'alias t=timetool' >> ~/.zshrc
```

## Examples

Convert from a unix timestamp to many other formats:
```
$ t 2303078400
2303078400
2042-12-25T00:00:00.000+00:00     Dec 25, 2042 0:00:00 UTC
2042-12-24T16:00:00.000-08:00     Dec 24, 2042 4:00:00 PM PST
Dec 25, 2042 0:00 UTC (Dec 24 4:00p PST)
```
(Note: all the examples on this page were ran from a computer in California, hence the automatic inclusion of Pacfic
Time ("PST" and "PDT") in all results)

Get the current time in many different timezones at once:
```
$ t now in ist,cst,cet
1640487650
2021-12-25T19:00:49.759-08:00     Dec 25, 2021 7:00:49 PM PST
2021-12-26T08:30:49.759+05:30     Dec 26, 2021 8:30:49 AM IST
2021-12-25T21:00:49.759-06:00     Dec 25, 2021 9:00:49 PM CST
2021-12-26T04:00:49.759+01:00     Dec 26, 2021 4:00:49 CET
2021-12-26T03:00:49.759+00:00     Dec 26, 2021 3:00:49 UTC
Dec 25, 2021 7:00:49 PM PST (Dec 26 8:30:49a IST / Dec 25 9:00:49p CST / Dec 26 4:00:49 CET / Dec 26 3:00:49 UTC)
```

Parse in a time string from an arbitrary timezone:
```
$ t October 10th 2023 1:30 am Australia/Sydney
1696861800
2023-10-10T01:30:00.000+11:00     Oct 10, 2023 1:30:00 AM AEDT
2023-10-09T07:30:00.000-07:00     Oct 09, 2023 7:30:00 AM PDT
2023-10-09T14:30:00.000+00:00     Oct 09, 2023 14:30:00 UTC
Oct 10, 2023 1:30 AM AEDT (Oct 09 7:30a PDT / Oct 09 14:30 UTC)
```

Display what time it was 7 hours ago:
```
$ t -7h
1640463095
2021-12-25T12:11:34.903-08:00     Dec 25, 2021 12:11:34 PM PST
2021-12-25T20:11:34.903+00:00     Dec 25, 2021 20:11:34 UTC
Dec 25, 2021 12:11:34 PM PST (20:11:34 UTC)
```

## Usage

```
Usage: timetool [-h] [TIME] [in CONVERSION_TIMEZONE] [-o][-e]

Examples:
  timetool
  timetool 1621108906
  timetool 1621108906000
  timetool 1621108906.000
  timetool May 15, 2021 01:01:46 PM PDT
  timetool 2021 May 15th 1:01 PM GMT-0700
  timetool 2021-05-15T20:01:46.000+00:00
  timetool 5pm PDT in CEST
  timetool now in Asia/Hong_Kong
  timetool now in IST,EDT,CEST,Asia/Tokyo
  timetool - 7d
  timetool + 1.5h
  timetool + 1mo
  timetool + 01:30:00

Help & support:
  https://github.com/personalcomputer/timetool/issues
```

## Credit

All the smarts in timetool are thanks to [dateutil](https://github.com/dateutil/dateutil), [pytz](https://pythonhosted.org/pytz/), [babel](https://github.com/python-babel/babel), the [CLDR](https://cldr.unicode.org/) and the [tz database](https://www.iana.org/time-zones).
