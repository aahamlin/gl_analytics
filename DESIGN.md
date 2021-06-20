# Design notes

## Command design classes

Need to run different commands, cumulative flow versus cycletime, which may have different sets of options.

The `argparse` module supports this through the `func` parameter.

### Common arguments

**Query arguments** in all cases we are searching for Issues in GitLab by one or more of:

- group
- milestone
- state

**Output arguments**
- outfile, filename to write results or stdout
- report, type of output, either CSV [text] or Plot [image/png]
- days, Range of history

To add/expose:
- type scope, identify Feature or Bug. Currently, type::*.


### Commands

1. Cumulative flow, Count of items by state per day

    Command arguments:

    - ylimit, set Plot ylimit (min,max). Default True.

    Future arguments:

    - workflow scoped label sets. (Currently, opened -> workflow::in progress -> workflow::code review -> closed)

2. Cycletime, Number of (business) days per item by day.

    Common cycletime calculation is from work begins to work completed, but we can calculate time spent in other [sub-]states of the workflow as well.

    Command arguments:

    - None

    Future arguments:

    - workflow scoped labels sub-states, e.g. in progress -> "code review" -> closed

## To do list

Given these 2 commmands

- add func for cflow and cycles https://docs.python.org/3/library/argparse.html#sub-commands
- rework main.Main.supported_reports functor
- use argparser filetype parameter for stdout writing https://docs.python.org/3/library/argparse.html#filetype-objects
- move scope Type::* Label resolver to its own AbstractResolver implementation
