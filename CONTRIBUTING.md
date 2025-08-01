# Contributing to the Tournament Project

First off, thank you for considering contributing to this project! It's people like you that make the open source community such a great place.

## Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/your-username/your-repository/issues/new)! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

If you have a general question, feel free to ask in the [discussions](https://github.com/your-username/your-repository/discussions).

## Fork & create a branch

If this is something you think you can fix, then [fork the repository](https://github.com/your-username/your-repository/fork) and create a branch with a descriptive name.

A good branch name would be (where issue #123 is the ticket you're working on):

```sh
git checkout -b 123-add-a-contributing-file
```

## Get the test suite running

Follow the installation instructions in `README.md` to set up your local development environment.

Once set up, you can run the test suite with the following command:

```sh
python manage.py test
```

## Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first :smile_cat:

For style, we follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.

## Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with the latest upstream version of the repository.

```sh
git remote add upstream git@github.com:your-username/your-repository.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```sh
git checkout 123-add-a-contributing-file
git rebase master
git push --force-with-lease origin 123-add-a-contributing-file
```

Finally, go to GitHub and [make a Pull Request](https://github.com/your-username/your-repository/compare/master...123-add-a-contributing-file)

## Keeping your Pull Request updated

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed, and that you need to update your branch so it's easier to merge.

To learn more about rebasing and merging, check out [this guide](https://www.atlassian.com/git/tutorials/merging-vs-rebasing).

## Merging a PR (for maintainers)

A PR can only be merged by a maintainer if it has at least one approval, and all status checks have passed.

A PR can be merged into the `master` branch by a maintainer by using the "Squash and merge" option.
