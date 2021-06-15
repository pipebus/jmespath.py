import argparse
import json
import os
import pprint
import sys

import jmespath

from .. import __version__
from .. import __project__

__description__ = "jpp is an extended superset of the jp CLI for JMESPath"

# This 2 space indent matches https://github.com/jmespath/jp behavior.
JP_COMPAT_DUMP_KWARGS = (
    ("indent", 2),
    ("ensure_ascii", False),
)


def decode_json_stream(stream):
    """
    Decode a text JSON input stream and generate objects until EOF.
    """
    eof = False
    line_buffer = []
    while line_buffer or not eof:
        progress = False
        if not eof:
            line = stream.readline()
            if line:
                progress = True
                line_buffer.append(line)
            else:
                eof = True

        if line_buffer:
            chunk = "".join(line_buffer)
            del line_buffer[:]

            try:
                yield json.loads(chunk)
                progress = True
            except json.JSONDecodeError as e:
                if e.pos > 0:
                    try:
                        yield json.loads(chunk[:e.pos])
                        progress = True
                    except json.JSONDecodeError:
                        # Raise if there's no progress, since a given
                        # chunk should be growning if it is not yet
                        # decodable.
                        if not progress:
                            raise
                        line_buffer.append(chunk)
                    else:
                        line_buffer.append(chunk[e.pos:])
                else:
                    raise


def jpp_main(argv=None):
    argv = sys.argv if argv is None else argv
    parser = argparse.ArgumentParser(
        prog=os.path.basename(argv[0]),
    )
    parser.add_argument("expression", nargs="?", default=None)
    parser.add_argument(
        "-c",
        "--compact",
        action="store_true",
        dest="compact",
        default=False,
        help=(
            "Produce compact JSON output that omits nonessential whitespace."
        ),
    )
    parser.add_argument(
        "-e",
        "--expr-file",
        dest="expr_file",
        default=None,
        help=(
            "Read JMESPath expression from the specified file."
        ),
    )
    parser.add_argument(
        "-f",
        "--filename",
        dest="filename",
        default=None,
        help=(
            "The filename containing the input data. "
            "If a filename is not given then data is "
            "read from stdin."
        ),
    )
    parser.add_argument(
        "-u",
        "--unquoted",
        action="store_false",
        dest="quoted",
        default=True,
        help=(
            "If the final result is a string, it will be printed without quotes."
        ),
    )
    parser.add_argument(
        "--ast",
        action="store_true",
        help=("Only print the AST of the parsed expression.  Do not rely on this output, only useful for debugging purposes."),
    )
    parser.usage = "{}\n  {} - {}".format(parser.format_usage().partition("usage: ")[-1], __project__, __description__)

    args = parser.parse_args(argv[1:])
    expression = args.expression
    if expression == "help":
        parser.print_help()
        return 1

    if expression and args.expr_file:
        parser.error("Only use one of the expression or --expr-file arguments.")

    dump_kwargs = dict(JP_COMPAT_DUMP_KWARGS)
    if args.compact:
        dump_kwargs.pop("indent", None)
        dump_kwargs["separators"] = (',', ':')

    if args.expr_file:
        with open(args.expr_file, "rt") as f:
            expression = f.read()

    if args.ast:
        # Only print the AST
        expression = jmespath.compile(args.expression)
        sys.stdout.write(pprint.pformat(expression.parsed))
        sys.stdout.write("\n")
        return 0

    if args.filename:
        f = open(args.filename, "rt")
    else:
        f = sys.stdin

    with f:
        for data in decode_json_stream(f):
            result = jmespath.search(expression, data)
            if args.quoted or not isinstance(result, str):
                result = json.dumps(result, **dump_kwargs)

            sys.stdout.write(result)
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(jpp_main(argv=sys.argv))
