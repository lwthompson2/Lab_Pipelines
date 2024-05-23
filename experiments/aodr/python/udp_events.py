import logging

import numpy as np

from pyramid.model.model import BufferData
from pyramid.model.events import TextEventList
from pyramid.neutral_zone.transformers.transformers import Transformer


class MessageTimesstamps(Transformer):
    """Parse timestamp info that our Open Ephys UDPEvents plugin appended to text messsages.

    The UDPEvents plugin is how we're enriching a small number of physical TTL lines with extra TTL and text events:

    https://github.com/benjamin-heasly/UDPEvents

    UDPEvents receives sync and text messages via UDP and writes text messages like these,
    with a @timestamp and a =sample_number appended to the text message bodies:

        - UDP Events sync on line 4@0.251607=79808
        - He who laughs last laughs ... you can't laugh again.@5.05543=271714
        - name=matlab,value=rSet('dXtarget',[4],'visible',1.00);draw_flag=1;,type=string@842.356=4212348
        - name=4930,type=unsigned long@842.369=4212738

    This parses out the @timestamps and updates each event's timestamp with the parsed value.
    """

    def __init__(
        self,
        timestamp_delimiter: str = "@",
        sample_number_delimiter: str = "=",
        **kwargs
    ) -> None:
        self.timestamp_delimiter = timestamp_delimiter
        self.sample_number_delimiter = sample_number_delimiter
        return None

    def parse_message(self, message: str) -> tuple[float, str]:
        parts = message.split(self.timestamp_delimiter, maxsplit=1)
        if len(parts) == 2:
            (message_prefix, timing_info) = parts
            timing_parts = timing_info.split(self.sample_number_delimiter, maxsplit=1)
            if len(timing_parts) == 2:
                (timestamp, _) = timing_parts
                return (float(timestamp), message_prefix)
        return (None, None)

    def update_events(self, events: TextEventList):
        for index in range(events.event_count()):
            raw_timestamp = events.timestamp_data[index]
            raw_text = events.text_data[index]
            try:
                # Split out message text along delimiters.
                (new_text, timing_info) = raw_text.split(self.timestamp_delimiter, maxsplit=1)
                (new_timestamp, sample_number) = timing_info.split(self.sample_number_delimiter, maxsplit=1)
                #print(f"{raw_timestamp}: {float(new_timestamp)} {sample_number} {new_text}")

                # Update the text event with parsed timestamp and text value, in place.
                #events.timestamp_data[index] = float(new_timestamp)
                events.text_data[index] = new_text
            except:
                logging.warning("Unable to parse timestamp from message: {raw_text}", exc_info=True)

    def transform(self, data: BufferData):
        if isinstance(data, TextEventList):
            self.update_events(data)
        else:
            logging.warning(f"UDPEventsMessageTimes doesn't know how to apply to {data.__class__.__name__}")
        return data
