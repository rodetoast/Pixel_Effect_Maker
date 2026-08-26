"""Runtime-only calculations shared by Resource and Effect timeline views."""
from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class TimelineTimeView:
    minimum_width:int=8
    maximum_width:int=160
    zoom_step:float=1.15

    def clamp_width(self,width):return max(self.minimum_width,min(self.maximum_width,int(round(width))))
    def zoom_width(self,width,wheel_steps):return self.clamp_width(float(width)*(self.zoom_step**int(wheel_steps)))
    def frame_coordinate(self,viewport_x,first_frame_x,width):return (float(viewport_x)-float(first_frame_x))/max(1,float(width))
    def frame_to_x(self,frame,first_frame_x,width):return float(first_frame_x)+(int(frame)+.5)*float(width)
    def anchored_scroll_delta(self,viewport_x,frame_coordinate,new_first_frame_x,new_width):return float(new_first_frame_x)+float(frame_coordinate)*float(new_width)-float(viewport_x)
    def fit_width(self,viewport_width,first_frame,last_frame,single_width=64):
        first,last=sorted((int(first_frame),int(last_frame)))
        if first==last:return self.clamp_width(min(single_width,max(self.minimum_width,int(viewport_width)//4)))
        return self.clamp_width(floor(max(1,int(viewport_width))/(last-first+3)))


def navigation_frame(frames,current,direction):
    values=sorted(set(int(value) for value in frames));current=int(current)
    candidates=[value for value in values if value>current] if int(direction)>0 else [value for value in values if value<current]
    return (min(candidates) if int(direction)>0 else max(candidates)) if candidates else None
