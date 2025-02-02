__all__ = ["CourseConfig"]

from typing import List, Optional, Union


class CourseConfig:

    def __init__(self, *,
                 _course_code: str,
                 _course_name: str,
                 _data_source_version: str,
                 _install_min_time: str,
                 _install_max_time: str,
                 _supported_dbrs: Union[str, List[str]],
                 _expected_dbrs: str):
        """
        The CourseConfig encapsulates those parameters that should never change for the entire duration of a course
        compared to the LessonConfig which encapsulates parameters that may change from lesson to lesson
        :param _course_code: See the property by the same name
        :param _course_name: See the property by the same name
        :param _data_source_version: See the property by the same name
        :param _install_min_time: See the property by the same name
        :param _install_max_time: See the property by the same name
        :param _supported_dbrs: See the property by the same name
        :param _expected_dbrs: See the property by the same name
        """

        from dbacademy.common import validate

        self.__course_code = validate.str_value(_course_code=_course_code, required=True)
        self.__course_name = validate.str_value(_course_name=_course_name, required=True)
        self.__build_name = CourseConfig.to_build_name(self.course_name)

        self.__data_source_version = validate.str_value(_data_source_version=_data_source_version, required=True)

        self.__install_min_time = validate.str_value(_install_min_time=_install_min_time, required=True)
        self.__install_max_time = validate.str_value(_install_max_time=_install_max_time, required=True)

        _supported_dbrs = [_supported_dbrs] if isinstance(_supported_dbrs, str) else _supported_dbrs
        validate.list_of_strings(_supported_dbrs=_supported_dbrs, required=True)
        self.__supported_dbrs = validate.list_value(_supported_dbrs=_supported_dbrs, min_length=1)

        self.__expected_dbrs = validate.str_value(_expected_dbrs=_expected_dbrs, required=True)

        # Verify that the expected and supported list of DBRs match.
        if self.expected_dbrs != "{{supported_dbrs}}":
            # This value is filled in at build time and ignored otherwise.
            expected_dbr_values = [e.strip() for e in self.expected_dbrs.split(",")]
            assert len(self.supported_dbrs) == len(expected_dbr_values), f"The supported and expected list of DBRs does not match: {len(self.supported_dbrs)} (supported) vs {len(expected_dbr_values)} (expected)"
            for dbr in self.supported_dbrs:
                assert dbr in expected_dbr_values, f"The supported DBR \"{dbr}\" was not find in the list of expected dbrs: {expected_dbr_values}"

    @property
    def course_code(self) -> str:
        """
        :return: the 2-4 character code for a course.
        """
        return self.__course_code

    @property
    def course_name(self) -> str:
        """
        :return: the name of the course.
        """
        return self.__course_name

    @property
    def build_name(self) -> str:
        """
        :return: the course_name after converting the value to lowercase and after converting all non-alpha and non-digits to a hyphen
        """
        return self.__build_name

    @staticmethod
    def to_build_name(course_name) -> Optional[str]:
        """
        Utility method to create a "build name" from a course name
        :param course_name: The name of the course
        :return: the build name where all non-alpha and non-digits are replaced with hyphens
        """
        import re

        if course_name is None:
            return None

        build_name = re.sub(r"[^a-zA-Z\d]", "-", course_name).lower()
        while "--" in build_name:
            build_name = build_name.replace("--", "-")
        return build_name

    @property
    def data_source_name(self) -> str:
        """
        This is assumed to be the same as build_name
        :return: the name of the dataset in the data repository.
        """
        return self.__build_name

    @property
    def data_source_version(self) -> str:
        """
        :return: the two-digit version number of a dataset prefixed by the letter "v" as in "v01" or "v02" (not to be confused with the version of a course)
        """
        return self.__data_source_version

    @property
    def install_min_time(self) -> str:
        """
        :return: the minimum amount of type required to "install" a dataset as measured from the curriculum-dev environment.
        """
        return self.__install_min_time

    @property
    def install_max_time(self) -> str:
        """
        :return: the maximum amount of time required to "install" a dataset as measured from, for example, Singapore - typically 2 or 3 times that of CourseConfig.install_min_time
        """
        return self.__install_max_time

    @property
    def supported_dbrs(self) -> List[str]:
        """
        Evaluated upon instantiation of DBAcademyHelper, this value ensures that the consumer's current DBR is one of the specified values.
        When an invalid DBR is used, a specific error message is generated for the user with explicit instructions on how to address the issue.
        See also DBAcademyHelper.__validate_spark_version
        :return: the list of DBRs for which this course is certified to run on.
        """
        return self.__supported_dbrs

    @property
    def expected_dbrs(self) -> str:
        """
        This value should always be set to "{{supported_dbrs}}". At build time, this value is substituted with the comma-seperated list
        of DBRs that are expressed as being supported from the perspective of the build tooling. This helps to ensure that the final set
        of supported DBRs expressed in the build tooling are always in sync with the published version of a course.
        :return: a comma seperated string of expected DBRs.
        """
        return self.__expected_dbrs
