from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Tags(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    is_nail_art: bool
    image_quality: Literal["high","medium","low","unknown"]
    colors: list[Literal["裸粉色","奶白色","酒红色","奶茶色","雾霾蓝","抹茶绿","焦糖棕","黑色","白色","红色","粉色","蓝色","绿色","紫色","黄色","橙色","灰色","金色","银色","透明","其他"]] = Field(max_length=8)
    styles: list[Literal["法式","猫眼","渐变","晕染","镜面","纯色","珍珠","碎钻","蝴蝶结","立体花朵","其他"]] = Field(max_length=6)
    nail_shape: Literal["短圆甲","圆甲","杏仁甲","方甲","方圆甲","尖甲","棺材甲","未知"]
    nail_length: Literal["短甲","中长甲","长甲","未知"]
    decorations: list[Literal["珍珠","碎钻","蝴蝶结","花朵","亮片","金属","贴纸","其他"]] = Field(max_length=8)
    finish: list[Literal["亮面","哑光","珠光","镜面","其他"]] = Field(max_length=4)
    scenes: list[Literal["通勤","约会","婚礼","度假","聚会","日常"]] = Field(max_length=3)
    seasons: list[Literal["春季","夏季","秋季","冬季"]] = Field(max_length=4)
    visual_evidence: str = Field(max_length=500)
    inference_evidence: str = Field(max_length=500)
    description: str = Field(max_length=500)
    confidence: float = Field(ge=0,le=1)
    inference_confidence: float = Field(ge=0,le=1)

    def result(self):
        data = self.model_dump()
        if not self.is_nail_art:
            for key in ("colors","styles","decorations","finish","scenes","seasons"):
                data[key] = []
            data["nail_shape"] = data["nail_length"] = "未知"
        for key in ("colors","styles","decorations","finish","scenes","seasons"):
            data[key] = list(dict.fromkeys(data[key]))
        data["need_review"] = (not self.is_nail_art or self.confidence < 0.75
                               or self.image_quality in ("low","unknown")
                               or bool(data["scenes"] or data["seasons"]) and self.inference_confidence < 0.65)
        return data
