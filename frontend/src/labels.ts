export const labels: Record<string,string> = {
 pending:'待处理',running:'运行中',success:'成功',failed:'失败',review:'待人工审核',manual:'人工已修正',idle:'空闲',unknown:'未知',warning:'有警告',success_with_warnings:'完成（有警告）',retry_wait:'等待重试',skipped:'已跳过',cancelled:'已取消',
 initialize:'初始化素材库',collect:'素材采集',frames:'视频抽帧',cluster:'图片聚类',primary_tags:'AI标签识别',recommendation:'场景季节推荐',recommend:'推荐规则',vectors:'视觉向量生成',validate:'数据完整性校验',export:'数据导出',sync:'远程归档',index:'向量生成',tags:'标签识别',pipeline:'完整流水线',resume:'断点恢复',
 is_nail_art:'是否为美甲内容',image_quality:'图片质量',colors:'颜色',styles:'款式',nail_shape:'甲型',nail_length:'甲长',decorations:'装饰元素',finish:'表面质感',scenes:'适用场景',seasons:'适用季节',visual_evidence:'视觉判断依据',inference_evidence:'推断依据',description:'素材描述',confidence:'识别置信度',inference_confidence:'推断置信度',content_type:'内容类型',nail_part:'美甲部位',design_visibility:'款式可见程度',style_evidence:'款式判断依据',need_review:'是否需要审核',review_reasons:'审核原因',recommendation_eligible:'是否符合推荐条件',
 high:'高',medium:'中',low:'低',finished:'美甲成品',process:'制作过程',product:'美甲产品',unrelated:'无关内容',hand:'手部',foot:'足部',both:'手部及足部',clear:'清晰',partial:'部分可见',none:'不可见',
 ValidationError:'标签结构校验失败',TimeoutError:'请求超时',ReadTimeout:'模型响应超时',ConnectError:'连接失败',content_type_conflict:'内容类型冲突',finished_design_not_clear:'成品款式不清晰',missing_color:'缺少颜色',potential_style_conflict:'款式可能冲突',mixed_finish_review:'表面质感混合，需审核',missing_style_evidence:'缺少款式判断依据',
 baidu:'百度图片',xiaohongshu:'小红书',douyin:'抖音',tiktok:'TikTok',import:'离线导入',detail:'详情采集'
}
export function zh(value: unknown): string {
 if(value==null || value==='') return '—'
 const key=String(value)
 if(key.startsWith('missing_style_evidence:')) return '缺少款式判断依据：'+key.split(':').slice(1).join(':')
 return labels[key] || key
}
export function stageLabel(value:unknown):string {
 return value==='review'?'备用模型复核':zh(value)
}
export function statusType(value:unknown):'success'|'warning'|'danger'|'info'|'primary' {
 if(value==='success'||value==='manual')return 'success'
 if(value==='failed')return 'danger'
 if(['review','warning','success_with_warnings','retry_wait'].includes(String(value)))return 'warning'
 return value==='running'?'primary':'info'
}
