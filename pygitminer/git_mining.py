# Copyright 2018 Safa Omri


import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Generator, Union

from git import Repo

from pygitminer.gitcommits import Commit
from pygitminer.gitrepo import GitRepository
from pygitminer.configuration import Conf

logger = logging.getLogger(__name__)


# This is the main class of pygitminer
class GitMining:
    

    def __init__(self, path_to_repo: Union[str, List[str]],
                 single: str = None,
                 since: datetime = None, to: datetime = None,
                 from_commit: str = None, to_commit: str = None,
                 from_tag: str = None, to_tag: str = None,
                 include_refs: bool = False,
                 include_remotes: bool = False,
                 reversed_order: bool = False,
                 only_in_branch: str = None,
                 only_modifications_with_file_types: List[str] = None,
                 only_no_merge: bool = False,
                 only_authors: List[str] = None,
                 only_commits: List[str] = None,
                 only_releases: bool = False,
                 filepath: str = None,
                 histogram_diff: bool = False,
                 skip_whitespaces: bool = False,
                 clone_repo_to: str = None,
                 order: str = None):
        file_modification_set = (
            None if only_modifications_with_file_types is None 
            else set(only_modifications_with_file_types)
            )
        commit_set = (
            None if only_commits is None
            else set(only_commits)
            )
        if reversed_order:
            logger.info("'reversed_order' is deprecated and will be removed in the next release. "
                        "Use 'order=reverse' instead. ")
            order = 'reverse'

        options = {
            "git_repo": None,
            "path_to_repo": path_to_repo,
            "from_commit": from_commit,
            "to_commit": to_commit,
            "from_tag": from_tag,
            "to_tag": to_tag,
            "since": since,
            "to": to,
            "single": single,
            "include_refs": include_refs,
            "include_remotes": include_remotes,
            "only_in_branch": only_in_branch,
            "only_modifications_with_file_types": file_modification_set,
            "only_no_merge": only_no_merge,
            "only_authors": only_authors,
            "only_commits": commit_set,
            "only_releases": only_releases,
            "skip_whitespaces": skip_whitespaces,
            "filepath": filepath,
            "filepath_commits": None,
            "tagged_commits": None,
            "histogram": histogram_diff,
            "clone_repo_to": clone_repo_to,
            "order": order
        }
        self._conf = Conf(options)

    @staticmethod
    def _is_remote(repo: str) -> bool:
        return repo.startswith("git@") or repo.startswith("https://")

    def _clone_remote_repos(self, tmp_folder: str, repo: str) -> str:

        repo_folder = os.path.join(tmp_folder,
                                   self._get_repo_name_from_url(repo))
        logger.info("Cloning %s in temporary folder %s", repo, repo_folder)
        Repo.clone_from(url=repo, to_path=repo_folder)

        return repo_folder

    def _clone_folder(self) -> str:
        if self._conf.get('clone_repo_to'):
            clone_folder = str(Path(self._conf.get('clone_repo_to')))
            if not os.path.isdir(clone_folder):
                raise Exception("Not a directory: {0}".format(clone_folder))
        else:
            clone_folder = tempfile.TemporaryDirectory().name
        return clone_folder

    def traverse_commits(self) -> Generator[Commit, None, None]:
        """
        Analyze all the specified commits (all of them by default), returning
        a generator of commits.
        """
        for path_repo in self._conf.get('path_to_repos'):
            if self._is_remote(path_repo):
                path_repo = self._clone_remote_repos(self._clone_folder(), path_repo)

            git_repo = GitRepository(path_repo, self._conf)
            self._conf.set_value("git_repo", git_repo)
            self._conf._check_filters()

            logger.info('Analyzing git repository in %s', git_repo.path)

            if self._conf.get('filepath') is not None:
                self._conf.set_value('filepath_commits', git_repo.get_modified_file(self._conf.get('filepath')))

            if self._conf.get('only_releases'):
                self._conf.set_value('tagged_commits', git_repo.get_tagged_commits())

            rev, kwargs = self._conf.build_args()

            for commit in git_repo.list_of_commits(rev, **kwargs):
                logger.info('Commit #%s in %s from %s', commit.hash, commit.committer_date, commit.author.name)

                if self._conf.is_commit_filtered(commit):
                    logger.info('Commit #%s filtered', commit.hash)
                    continue

                yield commit

            # cleaning, this is necessary since GitPython issues on memory leaks
            self._conf.set_value("git_repo", None)
            git_repo.clear()

    @staticmethod
    def _get_repo_name_from_url(url: str) -> str:
        last_slash_index = url.rfind("/")
        last_suffix_index = url.rfind(".git")
        if last_suffix_index < 0:
            last_suffix_index = len(url)

        if last_slash_index < 0 or last_suffix_index <= last_slash_index:
            raise Exception("Badly formatted url {}".format(url))

        return url[last_slash_index + 1:last_suffix_index]
