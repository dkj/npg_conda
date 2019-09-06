#!/usr/bin/env python
#
# Copyright © 2019 Genome Research Ltd. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# @author Keith James <kdj@sanger.ac.uk>

import logging as log

import argparse
import os
import sys
import subprocess
import time

import rfc3987

def docker_pull(image):
    subprocess.check_output(['docker', 'pull', image])


DEFAULT_RECIPES_DIR=os.path.expandvars("$HOME/conda-recipes")
DEFAULT_RECIPES_MOUNT="/home/conda/recipes"

DEFAULT_ARTEFACTS_DIR=os.path.expandvars("$HOME/conda-artefacts")
DEFAULT_ARTEFACTS_MOUNT="/opt/conda/conda-bld"

IRODS_BUILD_IMAGE="wsinpg/ub-12.04-conda-irods:0.3"
DEFAULT_BUILD_IMAGE="wsinpg/ub-12.04-conda:0.3"

description = """

Runs conda build in the specified Docker image. This script expects
input on STDIN consisting of 3 whitespace-separated fields per line
for each package to be built:

<package name> <package version> <path to recipe>

This input is normally generated by the accompanying package_sort.py
script which sorts packages so that dependencies are built first.

"""

parser = argparse.ArgumentParser(
    description=description,
    formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument("--recipes-dir",
                    help="Host recipes directory, "
                    "defaults to {}".format(DEFAULT_RECIPES_DIR),
                    type=str, nargs="?", default=DEFAULT_RECIPES_DIR)
parser.add_argument("--recipes-mount",
                    help="Container recipes mount, "
                    "defaults to {}".format(DEFAULT_RECIPES_MOUNT),
                    type=str, nargs="?", default=DEFAULT_RECIPES_MOUNT)

parser.add_argument("--artefacts-dir",
                    help="Host build artefacts directory, "
                    "defaults to {}".format(DEFAULT_ARTEFACTS_DIR),
                    type=str, nargs="?", default=DEFAULT_ARTEFACTS_DIR)
parser.add_argument("--artefacts-mount",
                    help="Container build artefacts mount, "
                    "defaults to {}".format(DEFAULT_ARTEFACTS_MOUNT),
                    type=str, nargs="?", default=DEFAULT_ARTEFACTS_MOUNT)

parser.add_argument("--build-channel",
                    help="The Conda channel from which to get dependencies "
                    "when not doing a full, local from-source build, "
                    "defaults to none (forcing a local build)",
                    type=str, nargs="?", default=None)

parser.add_argument("--irods-build-image",
                    help="The Docker image used to build iRODS, "
                    "defaults to {}".format(IRODS_BUILD_IMAGE),
                    type=str, nargs="?", default=IRODS_BUILD_IMAGE)
parser.add_argument("--conda-build-image",
                    help="Docker image used to build packages, "
                    "defaults to {}".format(DEFAULT_BUILD_IMAGE),
                    type=str, nargs="?", default=DEFAULT_BUILD_IMAGE)
parser.add_argument("--remove-container",
                    help="Remove the Docker container after each build",
                    action="store_true")

parser.add_argument("--dry-run",
                    help="Log the recipes that would be built at INFO level, "
                    "but do not build anything",
                    action="store_true")
parser.add_argument("--debug",
                    help="Enable DEBUG level logging to STDERR",
                    action="store_true")
parser.add_argument("--verbose",
                    help="Enable INFO level logging to STDERR",
                    action="store_true")

args = parser.parse_args()

level = log.ERROR
if args.debug:
    level = log.DEBUG
elif args.verbose or args.dry_run:
    level = log.INFO
log.basicConfig(level=level)

if args.build_channel:
    try:
        rfc3987.parse(args.build_channel, rule='URI')
    except ValueError as e:
        log.error("Invalid --build-channel URL '%s'", args.build_channel)
        exit(1)

docker_pull(args.conda_build_image)

fail = False

for line in sys.stdin.readlines():
    line.rstrip();
    name, version, path = line.split()
    log.info("Working on %s %s %s", name, version, path)

    build_image = args.conda_build_image
    if name == "irods":
        build_image = args.irods_build_image
        log.info("Using image %s", build_image)
        docker_pull(args.irods_build_image)

    build_script = \
        'export CONDA_BLD_PATH="{}" ; '.format(args.artefacts_mount)
    build_script += \
        'conda config --set auto_update_conda False ; '

    if args.build_channel:
        build_script += \
            'conda config --add channels {} ; '.format(args.build_channel)

    build_script += \
        'cd "{}" && conda build {}'.format(args.recipes_mount, path)

    run_cmd = ['docker', 'run']
    mount_args = ['--mount',
                  'source={},target={},type=bind'.format(args.recipes_dir,
                                                         args.recipes_mount),
                  '--mount',
                  'source={},target={},type=bind'.format(args.artefacts_dir,
                                                         args.artefacts_mount)]
    env_args = ['-e', 'CONDA_USER_ID=1000']
    other_args = ['-i']
    script_args = ['/bin/sh', '-c', build_script]

    if args.remove_container:
        other_args.append('--rm')

    cmd = run_cmd + mount_args + env_args + other_args + [build_image] \
        + script_args

    if args.dry_run:
        log.info('Docker command: "%s"', cmd)
    else:
        log.debug('Build script: "%s"', build_script)

        try:
            enc = sys.getfilesystemencoding()

            # Combine STDOUT and STDERR
            output = subprocess.run(cmd, check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            log.debug("########## BEGIN process STDOUT/STDERR ##########")
            for outline in output.stdout.decode(enc).split("\n"):
                log.debug(outline)
            log.debug("########## END process STDOUT/STDERR ##########")
        except subprocess.CalledProcessError as e:
            fail = True
            log.error("########## BEGIN process STDOUT/STDERR ##########")
            for errline in e.stdout.decode(enc).split("\n"):
                log.error(errline)
            log.error("########## END process STDOUT/STDERR ##########")

if fail:
    exit(1)
