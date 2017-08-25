..
    This file is part of hepcrawl.
    Copyright (C) 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.


Basic development flow
++++++++++++++++++++++

Git configuration
#################

First of all we have to set up some basic git configuration values:

* Set up the user info that will be used by Git as author and commiter for
  each commit.

.. code-block:: console

    $ git config --global user.name "name surname"
    $ git config --global user.email "your@email.here"


* Configure git to add the `Signed-off-by` header on each commit:

.. code-block:: console

    $ git config --global format.signoff true


Recommended: configure your ssh key on GitHub
#############################################

That will allow you to easily access the git repositories without having to
enter you user and password every time in a secure manner.

If you don't have one already, create an ssh key:

.. code-block:: console

    ssh-keygen

It will ask for a path and a password, the password is optional.

Now go to the `github settings page for keys`_ and add the contents of the
public key you just created, by default `~/.ssh/id_rsa.pub`.

.. warning::

    Never share you private key with anybody! (by default ~/.ssh/id_rsa)


Throughout this guide you will see also some tips that use it.


Clone the code
##############

Navigate to your work directory (or wherever you want to put the code) and
clone the main repository from github:

.. code-block:: console

    $ cd ~/Work  # or wherever you want to store the repo
    $ git clone git@github.com:inspirehep/hepcrawl
    $ cd hepcrawl


You will need also to add your personal fork, to do so just:

.. code-block:: console

    $ git remote add <your_gh_user> git@github.com:<your_gh_user>/hepcrawl

Replacing `<your_gh_user>` with your github username.

Now to make sure you have the correct remotes set up, you can run:

.. code-block:: console

    $ git remote -v

And that should show two, one called `origin` that points to the inspirehep
repo, and one called `<your_gh_user>` that points to your fork.

If for any reason you messed up or want to change the url or add/remove a
remote, check the commands:

.. code-block:: console

    $ git remote add <name> <url>
    $ git remote remove <name>
    $ git remote set-url <url>


Create your feature branch
##########################

Before starting to make changes, you should create a branch for them:

.. code-block:: console

    $ git checkout -b add_feature_x


It's a good habit to name your feature branch in a way that hints about what it
is adding/fixing/removing, for example, instead of `my_changes` it's way better
to have `adds_user_auth_to_workflows`.


Apply your changes
##################

Now you can start modifying, adding or removing files, try to create commits
regularly, and avoid mixing up changes on the same commit. For example, commit
any linting changes to existing code in a different commit to the addition of
code, or the addition of the tests.

To commit the changes:

.. code-block:: console

    $ git add <modified_file>
    $ git rm <file_to_delete>
    $ git add <any_new_file>
    $ git commit -s


About the commit message structure, we try to follow the `Invenio commit
guideline`_, but we put a strong emphasis in the content, specially:

* Describe why you did the change, not what the change is (the diff already
  shows the what).

* In the message body, add as many information as you need, it's better to be
  extra verbose than the alternative.

* If it addresses an issue, add the comment `closes #1234` to the description,
  where `#1234` is the issue number on github.


Create a pull request
#####################

As soon as you have worked some time doing changes, it's recommended to share
them, even if they are not ready yet, so in case that there's a misunderstanding
on how to do the change, you don't find out after spending a lot of time on it.

To create the pull request, first you have to push your changes to your
repository:

.. code-block:: console

    $ git push <your_gh_user> <add_feature_x> -f

.. note::
    The `-f` flag is required if it's not the first time you push, and you
    rebased you changes in between.

Now you can go to your github repo page, and create a new pull request, that
will ask you to specify a new message and description for it, if you had
multiple commits, try to summarize them there, that will help with the review.

.. warning::

    At this point, travis will test your changes and give you some feedback on
    github. To avoid ping-ponging with travis and save you some time, it's
    highly recommended to run the tests locally first, that will also allow you
    to debug any issues.

By default, your pull request will start with the flag `WIP`, while this is
set, you can push to it as many times as you want. Once your changes are ready
to be reviewed, add the `Need: Review` flag and remove the `WIP`. It's also
recommended to request a review directly to someone if you know that she's good
in the domain of the pull request.


Update your changes
###################

Some pull requests might take some time to merge, and other changes get merged
before to master. That might generate some code conflicts or make your tests
fail (or force you to change some of your code).

To resolve that issue, you should rebase on the latest master branch
periodically (try to do it at the very least once a day).

To do so:
* Fetch changes from the remotes:

.. code-block:: console

    $ git fetch --all

* Rebase your code and edit, drop, squash, cherry-pick and/or reword commits.
  This step will force you to resolve any conflicts that might arise.

.. code-block:: console

    $ git rebase -i origin/master

* Run the tests again to make sure nothing got broken.


Documentation
#############

Same as tests, documentation is part of the development process, so whenever
you write code, you should keep this priorities in mind:

* Very readable code is best.
* Good comments is good.
* Extra documentation is ok.

Documentation will be required though for some parts of the code meant to be
reused several times, like API's, utility functions, etc.

The format of the docstrings that we use is the Google style one defined in the
`Napoleon Sphinx extension page`_.


More details
############

Some useful links are listed bellow:

`Official git documentation
<https://git-scm.com/book/en/v2/>`_

`Git branching tutorial
<http://learngitbranching.js.org/>`_

`General git tutorial
<https://codewords.recurse.com/issues/two/git-from-the-inside-out>`_


.. _github settings page for keys: https://github.com/settings/keys
.. _Invenio commit guideline: http://invenio.readthedocs.io/en/latest/technology/git.html#r2-remarks-on-commit-log-messages
.. _Napoleon Sphinx extension page: http://www.sphinx-doc.org/en/stable/ext/napoleon.html
