# HOWTO create a new Conda recipe for, build and deploy a package #


## Ensure that you hava Conda available ##

We use the [Miniconda](https://conda.io/miniconda.html) version of
Conda. Your `$HOME/.condarc` file should look like this:

```bash
show_channel_urls: true

channels:
  - https://dnap.cog.sanger.ac.uk/npg/conda/prod/generic/
  - defaults
```

The public channel URLs are structured by channel purpose (`prod`, for
production, `test` for testing), OS distribution name (e.g. `Ubuntu`,
`RedHat`) and OS release number (e.g. `18.04` for Ubuntu Bionic, `7`
for RedHat Enterprise Linux).

Unless you are building a complete stack from scratch, you should have
a single channel defined, in addition to the `defaults` channel, from
which your new package's dependencies may be obtained at build time.

Conda does not include by default the tools required to build a new
package from a recipe. You should ensure that the `conda-build` Conda
package is installed in the base environment by running

```bash
conda install conda-build
```

## Read the software license ##

You *must* ensure the license of the software you are packaging
permits redistribution if the channel is public. Our main channels are
exposed as public URLs which means that they are suitable only for
[open-source software](https://en.wikipedia.org/wiki/Open-source_software).


## Create a new Conda recipe ##

A basic recipe consists of two files; `meta.yaml` (N.B. *not*
`meta.yml`) and `build.sh` which contain respectively, the metadata
about a recipe and the shell commands to build and install the
software into the package being created.

Further details may be found in the
[Conda build recipes](https://conda.io/docs/user-guide/tasks/build-packages/recipe.html)
section of the
[Conda User guide](https://conda.io/docs/user-guide/index.html)

The shell commands in `build.sh` must direct the install into a
special temporary directory created by Conda during the packaging
process. Conda sets and environment variable `$PREFIX` for this
purpose.

It is critical that the `meta.yaml` file contains an explicit build
version, starting at `0` and incrementing each time a change is made
to any part of the recipe.

The recipe must be placed in the `recipes` directory using the
heirarchy convention of `recipes/[package name]/[package version]/`


## Build the recipe ##

See README.md for detailed build instructions.

## Add the package to a channel ##

When your package is built, the next step is to publish it to a Conda
channel.

### Indexing the channel directory locally ###

A Conda channel is a URL pointing to an indexed directory of package
files. To add a new package to the channel, the file must be added to
the directory and the index rebuilt. This should be accomplished
locally, so you will need a local copy of the channel contents. If you
do not have access to a copy, then you can create a new (perhaps
temporary) copy by downloading the existing channel from `S3`.

To download the raw channel content using an `s3://` URL you will need
a WSI S3 account and an S3 client. The following example uses the
`s3cmd` client


```bash
s3cmd get -r s3://[bucket name]/npg/conda/prod/generic

```

Now that you have a local copy, add the new package and update the
index

```bash
conda index ./npg/conda/prod/generic
```

### Synchronizing with the remote channel ###

Once the local copy is indexed, synchronize the changes back to S3,
ensuring that the ACLs for any new files are public. This means that
*anyone* may freely download these files using the `https://` URL of
the channel.

This requires an S3 client, which is best installed using Python's pip
package manager into a Python virtualenv or Conda environment.

Using s3cmd:

```bash
s3cmd -c ~/.s3cfg-npg sync --acl-public --exclude '*/.cache/*' \
    ./prod/generic/ s3://[bucket name]/npg/conda/prod/generic/
```

or, using aws-cli:

```bash
aws s3 sync --acl public-read --exclude '*/.cache/*' \
    ./prod/generic/ s3://[bucket name]/npg/conda/prod/generic/
```

To give other WSI users permission to fully control the S3 bucket
contents:

```bash
s3cmd --acl-grant=full_control:[WSI user name] --recursive \
    s3://[bucket name]/npg/
```
