import getopt
import os
import sys

from colorama import init

from .api import *
from .gpxcompiler import *
from .utils import *

init()
interactive_info_shown = False


def usage():
    print(bcolor.HEADER + bcolor.BOLD + 'komootgpx.py [options]' + bcolor.ENDC)

    print(bcolor.OKBLUE + '[Authentication]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-m', '--mail=mail_address', 'Login using specified email address'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-p', '--pass=password', 'Use provided password and skip interactive prompt'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-n', '--anonymous', 'Skip authentication, no interactive prompt, valid only with -d'))

    print(bcolor.OKBLUE + '[Tours]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-l', '--list-tours', 'List all tours of the logged in user'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-d', '--make-gpx=tour_id', 'Download tour as GPX'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-a', '--make-all', 'Download all tours'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-s', '--skip-existing', 'Do not download and save GPX if the file already exists, ignored with -d'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-D', '--add-date', 'Add date to file name'))

    print(bcolor.OKBLUE + '[Filters]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-f', '--filter=type', 'Filter by track type (either "planned" or "recorded")'))

    print(bcolor.OKBLUE + '[Generator]' + bcolor.ENDC)
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-o', '--output', 'Output directory (default: working directory)'))
    print('\t{:<2s}, {:<30s} {:<10s}'.format('-e', '--no-poi', 'Do not include highlights as POIs'))


def notify_interactive():
    global interactive_info_shown
    interactive_info_shown = True
    if interactive_info_shown:
        print("Interactive mode. Use '--help' for usage details.")


def make_gpx(tour_id, api, output_dir, no_poi, skip_existing, tour_base, add_date):
    tour = None
    if tour_base is None:
        tour_base = api.fetch_tour(str(tour_id))
        tour = tour_base

    # Example date: 2022-01-02T12:26:41.795+01:00
    # :10 extracts "2022-01-02" from this.
    date_str = tour_base['date'][:10]+'_' if add_date else ''

    path = f"{output_dir}/{date_str}{sanitize_filename(tour['name'])}-{tour_id}.gpx"

    if skip_existing and os.path.exists(path):
        print_success(f"{tour_base['name']} skipped - already exists at '{path}'")
        return

    if tour is None:
        tour = api.fetch_tour(str(tour_id))
    gpx = GpxCompiler(tour, api, no_poi)

    f = open(path, "w", encoding="utf-8")
    f.write(gpx.generate())
    f.close()

    print_success(f"GPX file written to '{path}'")


def main(argv):
    tour_selection = ''
    mail = ''
    pwd = ''
    print_tours = False
    no_poi = False
    skip_existing = False
    add_date = False
    anonymous = False
    typeFilter = "all"
    output_dir = os.getcwd()

    try:
        opts, args = getopt.getopt(argv, "ahlesDno:d:m:p:f:",
            ["add-date", "list-tours", "make-gpx=", "mail=", "pass=", "filter=", "no-poi", "output=", "skip-existing", "make-all", "anonymous"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)

        elif opt in ("-f", "--filter"):
            typeFilter = "tour_" + str(arg)

        elif opt in ("-l", "--list-tours"):
            print_tours = True

        elif opt in ("-e", "--no-poi"):
            no_poi = True

        elif opt in ("-s", "--skip-existing"):
            skip_existing = True

        elif opt in ("-n", "--anonymous"):
            anonymous = True

        elif opt in ("-D", "--add-date"):
            add_date = True

        elif opt in ("-d", "--make-gpx"):
            tour_selection = str(arg)

        elif opt in ("-m", "--mail"):
            mail = str(arg)

        elif opt in ("-p", "--pass"):
            pwd = str(arg)

        elif opt in ("-o", "--output"):
            output_dir = str(arg)

        elif opt in ("-a", "--make-all"):
            tour_selection = "all"


    if anonymous and tour_selection == "all":
        print_error("Cannot get all user's routes in anonymous mode, use -d")
        sys.exit(2)

    if anonymous and (mail != "" or pwd != ""):
        print_error("Cannot specify login/password in anonymous mode")
        sys.exit(2)

    api = KomootApi()

    if not anonymous:
        if mail == "":
            notify_interactive()
            mail = prompt("Enter your mail address (komoot login)")

        if pwd == "":
            notify_interactive()
            pwd = prompt_pass("Enter your password (input hidden)")

        api.login(mail, pwd)

        if print_tours:
            api.print_tours(typeFilter)
            sys.exit(0)

        tours = api.fetch_tours(typeFilter)

    if tour_selection == "":
        notify_interactive()
        if not anonymous:
            api.print_tours(typeFilter)
        tour_selection = prompt("Enter a tour id to download")

    if not anonymous and tour_selection != "all" and int(tour_selection) not in tours:
        print_warning(f"Warning: This id ({tour_selection}) is not one of your tours. Use --list-tours to view complete list.")

    if tour_selection == "all":
        for x in tours:
            make_gpx(x, api, output_dir, no_poi, skip_existing, tours[x], add_date)
    else:
        if anonymous:
            make_gpx(tour_selection, api, output_dir, no_poi, False, None, add_date)
        else:
            if int(tour_selection) in tours:
                make_gpx(tour_selection, api, output_dir, no_poi, skip_existing, tours[tour_selection], add_date)
            else:
                make_gpx(tour_selection, api, output_dir, no_poi, skip_existing, None, add_date)
    print()


def entrypoint():
    try:
        return main(sys.argv[1:])
    except KeyboardInterrupt:
        print()
        print_error("Aborted by user")
        sys.exit(1)