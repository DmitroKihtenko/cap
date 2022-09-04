from datetime import datetime, timedelta
import hashlib


class ConfigFileLoader:
    def __init__(self, filename: str):
        self.filename = filename

        self.__last_read = None
        self.__read_interval = 3
        self.__cached_value = None
        self.__file_hash = None
        self.__is_changed = False

    def _read_file(self) -> bytes:
        try:
            self.__last_read = datetime.now()
            with open(self.filename, "rb") as file:
                return file.read()
        except IOError:
            raise IOError(
                f"Config file '{self.filename}' reading error"
            )

    def _calculate_hash(self, value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    @property
    def seconds_interval(self) -> float:
        return self.__read_interval

    @seconds_interval.setter
    def seconds_interval(self, interval: float):
        self.__read_interval = interval

    @property
    def filename(self) -> str:
        return self.__filename

    @filename.setter
    def filename(self, name: str):
        self.__filename = name

    @property
    def is_changed(self) -> bool:
        return self.__is_changed

    def get_file_value(self) -> bytes:
        if self.__cached_value is None:
            self.__cached_value = self._read_file()
            self.__file_hash = self._calculate_hash(
                self.__cached_value
            )
        return self.__cached_value

    def reset_changed(self):
        self.__is_changed = False

    def do_load(self):
        if (
                not self.__is_changed and
                self.__last_read is None or
                self.__last_read + timedelta(
                    seconds=self.seconds_interval
                ) <= datetime.now()
        ):
            self.__cached_value = self._read_file()
            hash_value = self._calculate_hash(
                self.__cached_value
            )
            if hash_value != self.__file_hash:
                self.__is_changed = True
                self.__file_hash = hash_value
