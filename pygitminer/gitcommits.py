# Copyright 2018 Safa Omri

import logging
from _datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional

import lizard
import lizard_languages
from git import Diff, Git, Commit as GitCommit, NULL_TREE


logger = logging.getLogger(__name__)


class MaintainabilityModelProperty(Enum):

    UNIT_SIZE = 1
    UNIT_COMPLEXITY = 2
    UNIT_INTERFACING = 3


class Method: 

    def __init__(self, func):
        self.name = func.name
        self.long_name = func.long_name
        self.filename = func.filename
        self.nloc = func.nloc
        self.complexity = func.cyclomatic_complexity
        self.token_count = func.token_count
        self.parameters = func.parameters
        self.start_line = func.start_line
        self.end_line = func.end_line
        self.fan_in = func.fan_in
        self.fan_out = func.fan_out
        self.general_fan_out = func.general_fan_out
        self.length = func.length
        self.top_nesting_level = func.top_nesting_level

    def __eq__(self, other):
        return self.name == other.name and self.parameters == other.parameters

    def __hash__(self):
        return hash(('name', self.name,
                     'long_name', self.long_name,
                     'params', (x for x in self.parameters)))

    # Threshold used in the Delta Maintainability Model to establish whether a method
    # is low risk in terms of its size.
    UNIT_SIZE_LOW_RISK_THRESHOLD = 15
    

    # Threshold used in the Delta Maintainability Model to establish whether a method
    # is low risk in terms of its cyclomatic complexity.
    UNIT_COMPLEXITY_LOW_RISK_THRESHOLD = 5
    

    # Threshold used in the Delta Maintainability Model to establish whether a method
    # is low risk in terms of its interface.
    UNIT_INTERFACING_LOW_RISK_THRESHOLD = 2
    

    def is_low_risk(self, dmm_prop: MaintainabilityModelProperty) -> bool:
        if dmm_prop is MaintainabilityModelProperty.UNIT_SIZE:
            return self.nloc <= Method.UNIT_SIZE_LOW_RISK_THRESHOLD
        if dmm_prop is MaintainabilityModelProperty.UNIT_COMPLEXITY:
            return self.complexity <= Method.UNIT_COMPLEXITY_LOW_RISK_THRESHOLD
        assert dmm_prop is MaintainabilityModelProperty.UNIT_INTERFACING
        return len(self.parameters) <= Method.UNIT_INTERFACING_LOW_RISK_THRESHOLD


# Type of Modification: ADD, COPY, RENAME, DELETE, MODIFY or UNKNOWN.
class ModificationType(Enum):

    ADD = 1
    COPY = 2
    RENAME = 3
    DELETE = 4
    MODIFY = 5
    UNKNOWN = 6


class Modification:  

    def __init__(self, old_path: str, new_path: str,
                 change_type: ModificationType,
                 diff_and_sc: Dict[str, str]):
        
        self._old_path = Path(old_path) if old_path is not None else None
        self._new_path = Path(new_path) if new_path is not None else None
        self.change_type = change_type
        self.diff = diff_and_sc['diff']
        self.source_code = diff_and_sc['source_code']
        self.source_code_before = diff_and_sc['source_code_before']

        self._nloc = None
        self._complexity = None
        self._token_count = None
        self._function_list = [] 
        self._function_list_before = []  

    @property
    # Return the total number of added lines in the file.
    def added(self) -> int:
        added = 0
        for line in self.diff.replace('\r', '').split("\n"):
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
        return added

    @property
    # Return the total number of removed lines in the file.
    def removed(self):
        removed = 0
        for line in self.diff.replace('\r', '').split("\n"):
            if line.startswith('-') and not line.startswith('---'):
                removed += 1
        return removed

    @property
    def old_path(self):
        if self._old_path is not None:
            return str(self._old_path)
        return None

    @property
    def new_path(self):  
        if self._new_path is not None:
            return str(self._new_path)
        return None

    @property
    def filename(self) -> str:  
        if self._new_path is not None and str(self._new_path) != "/dev/null":
            path = self._new_path
        else:
            path = self._old_path

        return path.name

    @property
    def language_supported(self) -> bool:  
        return lizard_languages.get_reader_for(self.filename) is not None

    @property
    def nloc(self) -> Optional[int]:  
        self._calculate_metrics()
        return self._nloc

    @property
    # Calculate the Cyclomatic Complexity of the file.
    def complexity(self) -> Optional[int]:  
        self._calculate_metrics()
        return self._complexity

    @property
    def token_count(self) -> Optional[int]: 
        self._calculate_metrics()
        return self._token_count

    @property
    def diff_parsed(self) -> Dict[str, List[Tuple[int, str]]]:
        lines = self.diff.split('\n')
        modified_lines = {'added': [], 'deleted': []}

        count_deletions = 0
        count_additions = 0

        for line in lines:
            line = line.rstrip()
            count_deletions += 1
            count_additions += 1

            if line.startswith('@@'):
                count_deletions, count_additions = self._get_line_numbers(line)

            if line.startswith('-'):
                modified_lines['deleted'].append((count_deletions, line[1:]))
                count_additions -= 1

            if line.startswith('+'):
                modified_lines['added'].append((count_additions, line[1:]))
                count_deletions -= 1

            if line == r'\ No newline at end of file':
                count_deletions -= 1
                count_additions -= 1

        return modified_lines

    @staticmethod
    def _get_line_numbers(line):
        token = line.split(" ")
        numbers_old_file = token[1]
        numbers_new_file = token[2]
        delete_line_number = int(numbers_old_file.split(",")[0].replace("-", "")) - 1
        additions_line_number = int(numbers_new_file.split(",")[0]) - 1
        return delete_line_number, additions_line_number

    @property
    def methods(self) -> List[Method]:
        self._calculate_metrics()
        return self._function_list

    @property
    def methods_before(self) -> List[Method]:
        self._calculate_metrics(include_before=True)
        return self._function_list_before

    @property
    def changed_methods(self) -> List[Method]:
        new_methods = self.methods
        old_methods = self.methods_before
        added = self.diff_parsed['added']
        deleted = self.diff_parsed['deleted']

        methods_changed_new = {y for x in added for y in new_methods if
                               y.start_line <= x[0] <= y.end_line}
        methods_changed_old = {y for x in deleted for y in old_methods if
                               y.start_line <= x[0] <= y.end_line}

        return list(methods_changed_new.union(methods_changed_old))

    @staticmethod
    def _risk_profile(methods: List[Method], dmm_prop: MaintainabilityModelProperty) -> Tuple[int, int]:
        low = sum([m.nloc for m in methods if m.is_low_risk(dmm_prop)])
        high = sum([m.nloc for m in methods if not m.is_low_risk(dmm_prop)])
        return low, high

    def _delta_risk_profile(self, dmm_prop: MaintainabilityModelProperty) -> Tuple[int, int]:
        assert self.language_supported
        low_before, high_before = self._risk_profile(self.methods_before, dmm_prop)
        low_after, high_after = self._risk_profile(self.methods, dmm_prop)
        return low_after - low_before, high_after - high_before

    def _calculate_metrics(self, include_before=False):
        if not self.language_supported:
            return

        if self.source_code and self._nloc is None:
            analysis = lizard.analyze_file.analyze_source_code(self.filename,
                                                               self.source_code)
            self._nloc = analysis.nloc
            self._complexity = analysis.CCN
            self._token_count = analysis.token_count

            for func in analysis.function_list:
                self._function_list.append(Method(func))

        if include_before and self.source_code_before and \
                not self._function_list_before:
            anal = lizard.analyze_file.analyze_source_code(
                self.filename, self.source_code_before)

            self._function_list_before = [
                Method(x) for x in anal.function_list]

    def __eq__(self, other):
        if not isinstance(other, Modification):
            return NotImplemented
        if self is other:
            return True
        return self.__dict__ == other.__dict__

class Developer:

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def __eq__(self, other):
        if not isinstance(other, Developer):
            return NotImplemented
        if self is other:
            return True

        return self.__dict__ == other.__dict__


class Commit:
    # parameter commit: GitPython Commit object
    # parameter conf: Configuration class
    def __init__(self, commit: GitCommit, conf) -> None:
        self._c_object = commit

        self._modifications = None
        self._branches = None
        self._conf = conf

    @property
    def hash(self) -> str:
        return self._c_object.hexsha

    @property
    def author(self) -> Developer:
        return Developer(self._c_object.author.name,
                         self._c_object.author.email)

    @property
    def committer(self) -> Developer:
        return Developer(self._c_object.committer.name,
                         self._c_object.committer.email)

    @property
    def project_name(self) -> str:
        return Path(self._conf.get('path_to_repo')).name

    @property
    def author_date(self) -> datetime:
        return self._c_object.authored_datetime

    @property
    def committer_date(self) -> datetime:
        return self._c_object.committed_datetime

    @property
    def author_timezone(self) -> int:
        return self._c_object.author_tz_offset

    @property
    def committer_timezone(self) -> int:
        return self._c_object.committer_tz_offset

    @property
    def msg(self) -> str:
        return self._c_object.message.strip()

    @property
    def parents(self) -> List[str]:
        parents = []
        for p in self._c_object.parents:
            parents.append(p.hexsha)
        return parents

    @property
    def merge(self) -> bool:
        return len(self._c_object.parents) > 1

    @property
    def modifications(self) -> List[Modification]:
        if self._modifications is None:
            self._modifications = self._get_modifications()

        assert self._modifications is not None
        return self._modifications

    def _get_modifications(self):
        options = {}
        if self._conf.get('histogram'):
            options['histogram'] = True

        if self._conf.get('skip_whitespaces'):
            options['w'] = True

        if len(self.parents) == 1:
            diff_index = self._c_object.parents[0].diff(self._c_object,
                                                        create_patch=True,
                                                        **options)
        elif len(self.parents) > 1:
            diff_index = []
        else:
            diff_index = self._c_object.diff(NULL_TREE,
                                             create_patch=True,
                                             **options)

        return self._parse_diff(diff_index)

    def _parse_diff(self, diff_index) -> List[Modification]:
        modifications_list = []
        for diff in diff_index:
            old_path = diff.a_path
            new_path = diff.b_path
            change_type = self._from_change_to_modification_type(diff)

            diff_and_sc = {
                'diff': self._get_decoded_str(diff.diff),
                'source_code_before': self._get_decoded_sc_str(
                    diff.a_blob),
                'source_code': self._get_decoded_sc_str(
                    diff.b_blob)
            }

            modifications_list.append(Modification(old_path, new_path,
                                                   change_type, diff_and_sc))

        return modifications_list

    def _get_decoded_str(self, diff):
        try:
            return diff.decode('utf-8', 'ignore')
        except (UnicodeDecodeError, AttributeError, ValueError):
            logger.debug('Could not load the diff of a '
                         'file in commit %s', self._c_object.hexsha)
            return None

    def _get_decoded_sc_str(self, diff):
        try:
            return diff.data_stream.read().decode('utf-8', 'ignore')
        except (UnicodeDecodeError, AttributeError, ValueError):
            logger.debug('Could not load source code of a '
                         'file in commit %s', self._c_object.hexsha)
            return None

    @property
    def in_main_branch(self) -> bool:
        return self._conf.get('main_branch') in self.branches

    @property
    def branches(self) -> Set[str]:
        if self._branches is None:
            self._branches = self._get_branches()

        assert self._branches is not None
        return self._branches

    def _get_branches(self):
        c_git = Git(str(self._conf.get('path_to_repo')))
        branches = set()
        for branch in set(c_git.branch('--contains', self.hash).split('\n')):
            branches.add(branch.strip().replace('* ', ''))
        return branches

    @property
    def delta_maintainability_model_unit_size(self) -> Optional[float]:
        return self._delta_maintainability(MaintainabilityModelProperty.UNIT_SIZE)

    @property
    def delta_maintainability_model_unit_complexity(self) -> Optional[float]:
        return self._delta_maintainability(MaintainabilityModelProperty.UNIT_COMPLEXITY)

    @property
    def delta_maintainability_model_unit_interfacing(self) -> Optional[float]:
        return self._delta_maintainability(MaintainabilityModelProperty.UNIT_INTERFACING)

    def _delta_maintainability(self, dmm_prop: MaintainabilityModelProperty) -> Optional[float]:
        delta_profile = self._delta_risk_profile(dmm_prop)
        if delta_profile:
            (delta_low, delta_high) = delta_profile
            dmm = self._good_change_proportion(delta_low, delta_high)
            if delta_low < 0 and delta_high == 0:
                assert dmm == 0.0
                dmm = 1.0
            assert 0.0 <= dmm <= 1.0
            return dmm
        return None

    def _delta_risk_profile(self, dmm_prop: MaintainabilityModelProperty) -> Optional[Tuple[int, int]]:
        supported_modifications = [mod for mod in self.modifications if mod.language_supported]
        if supported_modifications:
            deltas = [mod._delta_risk_profile(dmm_prop) for mod in supported_modifications]  #pylint: disable=W0212
            delta_low = sum(dlow for (dlow, dhigh) in deltas)
            delta_high = sum(dhigh for (dlow, dhigh) in deltas)
            return delta_low, delta_high
        return None

    @staticmethod
    def _good_change_proportion(low_risk_delta: int, high_risk_delta: int) -> float:
        bad_change, good_change = (0, 0)

        if low_risk_delta >= 0:
            good_change = low_risk_delta
        else:
            bad_change = abs(low_risk_delta)
        if high_risk_delta >= 0:
            bad_change += high_risk_delta
        else:
            good_change += abs(high_risk_delta)

        assert good_change >= 0 and bad_change >= 0

        total_change = good_change + bad_change
        result = good_change / total_change if total_change > 0 else 1.0
        assert 0.0 <= result <= 1.0

        return result

    @staticmethod
    def _from_change_to_modification_type(diff: Diff):
        if diff.new_file:
            return ModificationType.ADD
        if diff.deleted_file:
            return ModificationType.DELETE
        if diff.renamed_file:
            return ModificationType.RENAME
        if diff.a_blob and diff.b_blob and diff.a_blob != diff.b_blob:
            return ModificationType.MODIFY

        return ModificationType.UNKNOWN

    def __eq__(self, other):
        if not isinstance(other, Commit):
            return NotImplemented
        if self is other:
            return True

        return self.__dict__ == other.__dict__
