"""
This file provides api for retrieving data from codeforces.com
"""

from enum import Enum

import json
from urllib import request

from api import Problem
from api import RanklistRow
from api import RatingChange
from api import Hack
from api import User
from api import ProblemStatistics
from api import Contest
from api import Submission


__all__ = ['CodeforcesAPI', 'CodeforcesLanguage']


class CodeforcesLanguage(Enum):
    en = 'en'
    ru = 'ru'


class CodeforcesDataRetriever:
    """
    This class hides low-level operations with retrieving data from Codeforces site
    """
    def __init__(self, lang=CodeforcesLanguage.en):
        """

        :param lang: Language
        :type lang: CodeforcesLanguage
        :return:
        """
        assert isinstance(lang, CodeforcesLanguage), \
            'lang should be of type CodeforcesLanguage, not {}'.format(type(lang))

        self._base_from_language = {
            CodeforcesLanguage.en: 'http://codeforces.com/api/',
            CodeforcesLanguage.ru: 'http://codeforces.ru/api/'
        }

        self._language = lang

    def get_data(self, method, **kwargs):
        """
        Retrieves data by given method with given parameters

        :param method: Request method
        :param kwargs: HTTP parameters
        :return:
        """
        return self.__get_data(self.__generate_url(method, **kwargs))

    def __get_data(self, url):
        """
        Returns data retrieved from given url
        """
        with request.urlopen(url) as req:
            return self.__check_json(req.readall().decode('utf-8'))

    def __generate_url(self, method, **kwargs):
        """
        Generates request url with given method and named parameters

        :param method: Name of the method
        :type method: str
        :param kwargs: HTTP parameters
        :type kwargs: dict of [str, object]
        :return: Url
        :rtype: str
        """
        url = self.base + method

        if kwargs:
            args = self.__get_valid_args(**kwargs)
            url += '?' + '&'.join(map(self.__key_value_to_http_parameter, args.items()))

        return url

    @staticmethod
    def __get_valid_args(**kwargs):
        """
        Filters only not None values
        """
        return {k: v for k, v in kwargs.items() if v is not None}

    @staticmethod
    def __key_value_to_http_parameter(key_value):
        """
        Transforms dictionary of values to http parameters
        """
        key, value = key_value

        if isinstance(value, list):
            value = ';'.join(value)
        else:
            value = str(value)

        return '{0}={1}'.format(key, value)

    @staticmethod
    def __check_json(answer):
        """
        Check if answer is correct according to http://codeforces.com/api/help
        """
        values = json.loads(answer)

        try:
            if values['status'] == 'OK':
                return values['result']
            else:
                raise ValueError(values['comment'])
        except KeyError as e:
            raise ValueError('Missed required field', e.args[0])

    @property
    def base(self):
        """
        :return: Base of url according to language
        :rtype: str
        """
        return self._base_from_language[self.language]

    @property
    def language(self):
        """
        :returns: Language. By default is en
        :rtype: CodeforcesLanguage
        """
        return self._language

    @language.setter
    def language(self, value):
        """
        :param value: Language
        :type value: CodeforcesLanguage or str
        """
        assert isinstance(value, (CodeforcesLanguage, str))
        self._language = CodeforcesLanguage(value)


class CodeforcesAPI:
    """
    This class provides api for retrieving data from codeforces.com
    """

    def __init__(self, lang='en'):
        """
        :param lang: Language
        :type lang: str or CodeforcesLanguage
        """
        self._data_retriever = CodeforcesDataRetriever(CodeforcesLanguage(lang))

    def contest_hacks(self, contest_id):
        """
        Returns list of hacks in the specified contests.

        Full information about hacks is available only after some time after the contest end.
        During the contest user can see only own hacks.

        :param contest_id: Id of the contest.
                           It is not the round number. It can be seen in contest URL. For example: /contest/374/status
        :type contest_id: int
        :return: Returns a list of Hack objects.
        :rtype: list of Hack
        """
        assert isinstance(contest_id, int)

        data = self._data_retriever.get_data('contest.hacks', contestId=contest_id)

        return list(map(Hack, data))

    def contest_list(self, gym=False):
        """
        Returns information about all available contests.

        :param gym: If true — than gym contests are returned. Otherwise, regular contests are returned.
        :type gym: bool
        :return: Returns a list of Contest objects. If this method is called not anonymously,
                 then all available contests for a calling user will be returned too,
                 including mashups and private gyms.
        :rtype: list of Contest
        """
        data = self._data_retriever.get_data('contest.list', gym=gym)

        return list(map(Contest, data))

    def contest_standings(self, contest_id, from_=1, count=None, handles=None):
        """
        Returns the description of the contest and the requested part of the standings.

        :param contest_id: Id of the contest. It is not the round number. It can be seen in contest URL.
                           For example: /contest/374/status
        :type contest_id: int

        :param from_: 1-based index of the standings row to start the ranklist.
        :type from_: int

        :param count: Number of standing rows to return.
        :type count: int

        :param handles: List of handles. No more than 10000 handles is accepted.
        :type handles: list of str

        :return: Returns object with three fields: "contest", "problems" and "rows".
                 Field "contest" contains a Contest object.
                 Field "problems" contains a list of Problem objects.
                 Field "rows" contains a list of RanklistRow objects.
        :rtype: {'contest': Contest,
                 'problems': list of Problem,
                 'rows': list of RanklistRow}
        """
        assert isinstance(contest_id, int), 'contest_id should be of type int, not {}'.format(type(contest_id))
        assert isinstance(from_, int), 'from_ should be of type int, not {}'.format(type(from_))
        assert isinstance(count, int) or count is None, 'count should be of type int, not {}'.format(type(count))
        assert isinstance(handles, list) or handles is None, \
            'handles should be of type list of str, not {}'.format(type(handles))
        assert len(handles) <= 10000, 'No more than 10000 handles is accepted'

        data = self._data_retriever.get_data('contest.standings',
                                             contestId=contest_id,
                                             count=count,
                                             handles=handles,
                                             **{'from': from_})

        return {'contest': list(map(Contest, data['contest'])),
                'problems': list(map(Problem, data['problems'])),
                'rows': list(map(RanklistRow, data['rows']))}

    def contest_status(self, contest_id, handle=None, from_=1, count=None):
        """
        Returns submissions for specified contest.

        Optionally can return submissions of specified user.

        :param contest_id: Id of the contest.
                           It is not the round number. It can be seen in contest URL. For example: /contest/374/status
        :type contest_id: int

        :param handle: Codeforces user handle.
        :type handle: str

        :param from_: 1-based index of the first submission to return.
        :type from_: int

        :param count: Number of returned submissions.
        :type count: int

        :return: Returns a list of Submission objects, sorted in decreasing order of submission id.
        :rtype: list of Submission
        """
        assert isinstance(contest_id, int)
        assert isinstance(handle, str) or handle is None
        assert isinstance(from_, int)
        assert isinstance(count, int) or count is None

        data = self._data_retriever.get_data('contest.status',
                                             contestId=contest_id,
                                             handle=handle,
                                             count=count,
                                             **{'from': from_})

        return list(map(Submission, data))

    def problemset_problems(self, tags=None):
        """
        Returns all problems from problemset. Problems can be filtered by tags.

        :param tags: List of tags.
        :type tags: list of str
        :return: Returns two lists. List of Problem objects and list of ProblemStatistics objects.
        :rtype: {'problems': list of Problem,
                 'problemStatistics': list of ProblemStatistics}
        """
        data = self._data_retriever.get_data('problemset.problems', tags=tags)

        return {'problems': list(map(Problem, data['problems'])),
                'problemStatistics': list(map(ProblemStatistics, data['problemStatistics']))}

    def problemset_recent_status(self, count):
        """
        Returns recent submissions.

        :param count: Number of submissions to return. Can be up to 1000.
        :type count: int

        :return: Returns a list of Submission objects, sorted in decreasing order of submission id.
        :rtype: list of Submission
        """
        assert isinstance(count, int)
        assert 0 < count <= 1000

        data = self._data_retriever.get_data('problemset.recentStatus', count=count)

        return list(map(Submission, data))

    def user_info(self, handles):
        """
        Returns information about one or several users.

        :param handles: List of handles. No more than 10000 handles is accepted.
        :type handles: list of str
        :return: Returns a list of User objects for requested handles.
        :rtype: list of User
        """
        assert isinstance(handles, list)

        data = self._data_retriever.get_data('user.info', handles=handles)

        return list(map(User, data))

    def user_rated_list(self, active_only=False):
        """
        Returns the list of all rated users.

        :param active_only: If true then only users, who participated in rated contest during the last month are
                            returned. Otherwise, all users with at least one rated contest are returned.
        :type active_only: bool
        :return: Returns a list of User objects, sorted in decreasing order of rating.
        :rtype: list of User
        """
        assert isinstance(active_only, bool)

        data = self._data_retriever.get_data('user.ratedList', activeOnly=active_only)

        return list(map(User, data))

    def user_rating(self, handle):
        """
        Returns rating history of the specified user.

        :param handle: Codeforces user handle.
        :type handle: str

        :return: Returns a list of RatingChange objects for requested user.
        :rtype: list of RatingChange
        """
        assert isinstance(handle, str), 'Handle should have str type, not {}'.format(type(handle))

        data = self._data_retriever.get_data('user.rating', handle=handle)

        return list(map(RatingChange, data))

    def user_status(self, handle, from_=1, count=None):
        """
        Returns submissions of specified user.

        :param handle: Codeforces user handle.
        :type handle: str
        :param from_: 1-based index of the first submission to return
        :type from_: int
        :param count: Number of returned submissions.
        :type count: int or None
        :return: Returns a list of Submission objects, sorted in decreasing order of submission id.
        :rtype: list of Submission
        """
        assert isinstance(handle, str)
        assert isinstance(from_, int)
        assert isinstance(count, int) or count is None

        data = self._data_retriever.get_data('user.status', handle=handle, count=count, **{'from': from_})

        return list(map(Submission, data))
