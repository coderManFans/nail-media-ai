<script setup lang="ts">
import {ref,onMounted} from 'vue'
type Item={image_sha:string;status?:string;score?:number;tags?:Record<string,any>}
const pages=['数据总览','素材管理','智能检索','标签管理','AI审核中心','任务管理','采集配置']
const page=ref('数据总览'),busy=ref(false),error=ref('')
const stats=ref<Record<string,number>>({}),items=ref<Item[]>([]),reviews=ref<any[]>([]),runs=ref<any[]>([]),steps=ref<any[]>([])
const collection=ref<any[]>([]),authorized=ref(false),schema=ref<Record<string, any>>({}),formTags=ref<Record<string,any>>({}),advanced=ref(false)
async function saveCollection(){await action(async()=>{collection.value=await request('/collection',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(collection.value.map(t=>({...t,keyword:t.keyword||''})))})})}
const job=ref<any>({}),kind=ref('index'),jobLimit=ref(10),draft=ref('')
async function refreshJob(){await action(async()=>{job.value=await request('/jobs')})}
async function startJob(){await action(async()=>{job.value=await request('/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:kind.value,limit:jobLimit.value,authorized:authorized.value})})})}
async function openItem(item:Item){selected.value=item;const tags={...item.tags};for(const key of ['need_review','review_reasons','recommendation_eligible'])delete tags[key];draft.value=JSON.stringify(tags,null,2);formTags.value=tags;advanced.value=false;await action(async()=>{schema.value=(await request('/tag-schema')).properties})}
async function saveReview(){if(!selected.value)return;await action(async()=>{const tags=await request('/assets/'+selected.value!.image_sha+'/review',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(advanced.value?JSON.parse(draft.value):formTags.value)});selected.value!.tags=tags;selected.value!.status='manual';selected.value=null})}
const total=ref(0),current=ref(1),state=ref(''),q=ref(''),color=ref(''),style=ref(''),shape=ref(''),include=ref(false),selected=ref<Item|null>(null)
const names:Record<string,string>={crawler_assets:'图片素材',video_assets:'视频素材',image_clusters:'图片聚类',image_tags:'标签记录',image_vectors:'视觉向量',tag_review_queue:'复核任务'}
const colors=['裸粉色','奶白色','酒红色','奶茶色','雾霾蓝','抹茶绿','焦糖棕','黑色','白色','红色','粉色','蓝色','绿色','紫色','金色','银色','透明']
const styles=['法式','猫眼','渐变','晕染','镜面','纯色','珍珠','碎钻','蝴蝶结','立体花朵']
const shapes=['短圆甲','圆甲','杏仁甲','方甲','方圆甲','尖甲','棺材甲']
const imageUrl=(sha:string)=>'/api/images/'+encodeURIComponent(sha)
async function request(path:string,options?:RequestInit){
 const r=await fetch('/api'+path,options)
 if(!r.ok) throw new Error('请求失败 HTTP '+r.status+' '+(await r.text()).slice(0,200))
 return r.json()
}
async function action(fn:()=>Promise<void>){
 busy.value=true;error.value=''
 try{await fn()}catch(e){error.value=String(e)}finally{busy.value=false}
}
async function load(){
 await action(async()=>{
 if(page.value==='采集配置') collection.value=await request('/collection')
 else if(page.value==='数据总览') stats.value=await request('/statistics')
 else if(page.value==='素材管理'){const r=await request('/assets?'+new URLSearchParams({limit:'24',offset:String((current.value-1)*24),state:state.value}));items.value=r.items;total.value=r.total}
 else if(page.value==='AI审核中心') reviews.value=await request('/reviews')
 else if(page.value==='任务管理'){const r=await request('/pipeline');runs.value=r.runs;steps.value=r.steps;job.value=await request('/jobs')}
 })
}
function navigate(p:string){page.value=p;items.value=[];current.value=1;void load()}
async function search(){
 await action(async()=>{items.value=await request('/search?'+new URLSearchParams({q:q.value,color:color.value,style:style.value,shape:shape.value,include_unreviewed:String(include.value),limit:'60'}))})
}
async function upload(e:Event){
 const input=e.target as HTMLInputElement
 const file=input.files?.[0];if(!file)return
 await action(async()=>{const data=new FormData();data.append('file',file);items.value=await request('/search/image?limit=30',{method:'POST',body:data})})
 input.value=''
}
onMounted(load)
</script>
<template>
 <div class="shell">
 <aside><div class="brand">NAIL<span>MEDIA AI</span><small>美甲素材工作台</small></div><button v-for="p in pages" :key="p" :class="{active:page===p}" @click="navigate(p)">{{p}}</button><footer>LOCAL WORKSPACE</footer></aside>
 <main><header><div><small>素材生产与检索 / {{page}}</small><h1>{{page}}</h1></div><el-button :loading="busy" @click="page==='智能检索'?search():load()">刷新</el-button></header>
 <el-alert v-if="error" :title="error" type="error" show-icon :closable="false"/>
 <section v-loading="busy">
 <template v-if="page==='数据总览'"><p class="muted">本地素材库实时统计</p><div class="metrics"><div class="panel" v-for="(v,k) in stats" :key="k"><small>{{names[k]||k}}</small><strong>{{v}}</strong></div></div><div class="panel"><h3>数据生产流程</h3><div class="process">采集 → 抽帧 → 聚类 → 标签 → 复核 → 推荐 → 归档</div></div></template>
 <template v-if="page==='素材管理'||page==='智能检索'">
 <div class="panel toolbar" v-if="page==='素材管理'"><el-select v-model="state" placeholder="全部状态" clearable @change="current=1;load()"><el-option label="成功" value="success"/><el-option label="待审核" value="review"/><el-option label="失败" value="failed"/></el-select><span>共 {{total}} 张</span></div>
 <div class="panel toolbar" v-else><el-input v-model="q" placeholder="英文描述，例如 pink cat eye nails" @keyup.enter="search"/><el-select v-model="color" placeholder="颜色" clearable><el-option v-for="x in colors" :key="x" :value="x"/></el-select><el-select v-model="style" placeholder="款式" clearable><el-option v-for="x in styles" :key="x" :value="x"/></el-select><el-select v-model="shape" placeholder="甲型" clearable><el-option v-for="x in shapes" :key="x" :value="x"/></el-select><el-checkbox v-model="include">包含未审核</el-checkbox><el-button type="primary" @click="search">搜索</el-button><label class="upload">上传图片<input type="file" accept="image/jpeg,image/png,image/webp" @change="upload"/></label></div>
 <div class="gallery"><article v-for="item in items" :key="item.image_sha" @click="openItem(item)"><img :src="imageUrl(item.image_sha)" loading="lazy" alt="美甲素材"/><div class="meta"><el-tag size="small" v-if="item.status">{{item.status}}</el-tag><small v-if="item.score!==undefined">得分 {{item.score.toFixed(3)}}</small><p>{{item.tags?.description||item.image_sha.slice(0,12)}}</p><el-tag v-for="tag in [...(item.tags?.colors||[]),...(item.tags?.styles||[])]" :key="tag" size="small" effect="plain">{{tag}}</el-tag></div></article></div>
 <el-empty v-if="!items.length" description="暂无匹配素材"/>
 <el-pagination v-if="page==='素材管理'" v-model:current-page="current" :page-size="24" :total="total" layout="prev,pager,next" @current-change="load"/>
 </template>
 <template v-if="page==='标签管理'"><div class="panel" v-for="group in [{name:'颜色',values:colors},{name:'款式',values:styles},{name:'甲型',values:shapes}]" :key="group.name"><h3>{{group.name}}</h3><el-tag v-for="x in group.values" :key="x" effect="plain">{{x}}</el-tag></div><p class="muted">当前为标签字典浏览，编辑功能尚未开放。</p></template>
 <template v-if="page==='AI审核中心'"><el-table :data="reviews"><el-table-column label="素材" width="100"><template #default="s"><img class="thumb" :src="imageUrl(s.row.image_sha)"/></template></el-table-column><el-table-column prop="state" label="状态"/><el-table-column prop="backup_model" label="复核模型"/><el-table-column label="异常或分歧"><template #default="s">{{s.row.detail.error||s.row.detail.differences?.join('、')||'—'}}</template></el-table-column></el-table><p class="muted">显示前100条复核记录，暂不支持人工修改。</p></template>
 <template v-if="page==='采集配置'"><div class="panel" v-for="t in collection" :key="t.id"><h3>{{t.platform}} / {{t.id}}</h3><div class="toolbar"><el-switch v-model="t.enabled"/><el-input v-model="t.keyword" placeholder="关键词（导入任务不按关键词搜索）"/><span>数量</span><el-input-number v-model="t.limit" :min="1" :max="20"/><span>周期（小时）</span><el-input-number v-model="t.interval_hours" :min="1" :max="8760"/></div></div><el-button type="primary" @click="saveCollection">保存配置</el-button><p>仅修改已有任务；采集需在 production.json 启用 collect。</p></template><template v-if="page==='任务管理'"><div class="panel"><h3>本地后台任务</h3><div class="toolbar"><el-select v-model="kind"><el-option label="向量生成" value="index"/><el-option label="AI标签" value="tags"/><el-option label="备用模型复核" value="review"/><el-option label="推荐规则" value="recommend"/><el-option label="完整流水线" value="pipeline"/><el-option label="断点恢复" value="resume"/></el-select><el-checkbox v-model="authorized">确认已获采集授权</el-checkbox><el-input-number v-model="jobLimit" :min="1" :max="100"/><el-button type="primary" :disabled="busy||job.state==='running'" @click="startJob">启动任务</el-button><el-button @click="refreshJob">刷新日志</el-button></div><p>状态：{{job.state||'idle'}}</p><pre>{{job.log||'暂无日志'}}</pre></div><h3>最近运行</h3><el-table :data="runs"><el-table-column prop="id" label="运行ID"/><el-table-column prop="state" label="状态"/></el-table><h3>最新运行阶段</h3><el-table :data="steps"><el-table-column prop="name" label="阶段"/><el-table-column prop="state" label="状态"/><el-table-column prop="seconds" label="耗时（秒）"/><el-table-column prop="payload" label="结果" show-overflow-tooltip/></el-table></template>
 </section></main>
 <el-dialog :model-value="!!selected" title="素材详情" width="min(720px,90vw)" @close="selected=null"><template v-if="selected"><img class="detail" :src="imageUrl(selected.image_sha)"/><p>人工标签修正（JSON，保留原始AI结果）</p><el-checkbox v-model="advanced" @change="(v:any)=>{if(v)draft=JSON.stringify(formTags,null,2);else{try{formTags=JSON.parse(draft)}catch{advanced=true}}}">高级 JSON 编辑</el-checkbox><el-input v-if="advanced" v-model="draft" type="textarea" :rows="14"/><div v-else v-for="(spec,key) in schema" :key="key" style="margin:12px 0"><label>{{key}}</label><el-select v-if="spec.enum||spec.items?.enum" v-model="formTags[key]" :multiple="!!spec.items" style="width:100%"><el-option v-for="v in (spec.enum||spec.items.enum)" :key="v" :value="v"/></el-select><el-switch v-else-if="spec.type==='boolean'" v-model="formTags[key]"/><el-input-number v-else-if="spec.type==='number'" v-model="formTags[key]" :min="0" :max="1" :step="0.05"/><el-input v-else-if="spec.type==='string'" v-model="formTags[key]"/><div v-else-if="key==='style_evidence'"><el-input v-for="s in (formTags.styles||[])" :key="s" :placeholder="s+' 视觉依据'" :model-value="formTags.style_evidence?.[s]||''" @update:model-value="(v:string)=>{formTags.style_evidence={...formTags.style_evidence,[s]:v}}"/></div></div><el-button type="primary" :loading="busy" @click="saveReview">保存人工标签</el-button></template></el-dialog>
 </div>
</template>
<style>
*{box-sizing:border-box}body{margin:0;background:#f7f6f8;color:#292432;font:14px system-ui,sans-serif}.shell{display:flex;min-height:100vh}aside{width:220px;flex-shrink:0;background:#282334;color:#fff;padding:28px 16px;position:sticky;top:0;height:100vh}.brand{font-size:23px;font-weight:800;letter-spacing:1px;margin:0 8px 36px}.brand span{color:#dca7c5}.brand small{display:block;font-size:12px;color:#c6bdce;margin-top:8px;font-weight:400}aside button{display:block;width:100%;text-align:left;border:0;background:transparent;color:#d8d0df;padding:14px 16px;border-radius:8px;margin:4px 0;cursor:pointer}aside button.active{background:#514057;color:white}footer{position:absolute;bottom:24px;font-size:10px;letter-spacing:2px;color:#a99bb2}main{flex:1;min-width:0;padding:30px;max-width:1600px}header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}header small,.muted{color:#817989}h1{font-size:28px;margin:8px 0}h3{margin-top:0}.panel{background:white;border:1px solid #ebe7ee;border-radius:12px;padding:20px;margin-bottom:18px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px}.metrics strong{display:block;font-size:34px;margin-top:14px}.process{line-height:2;color:#72536f}.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.toolbar .el-input{flex:1;min-width:220px}.toolbar .el-select{width:130px}.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px;margin:20px 0}.gallery article{background:white;border:1px solid #ebe7ee;border-radius:12px;overflow:hidden;cursor:pointer}.gallery img{width:100%;aspect-ratio:1;object-fit:cover;display:block}.meta{padding:12px}.meta p{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.el-tag{margin:3px}.thumb{width:64px;height:64px;object-fit:cover;border-radius:6px}.detail{max-width:100%;max-height:400px;display:block;margin:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}.upload{cursor:pointer;border:1px solid #dcdfe6;border-radius:5px;padding:8px 14px;background:white}.upload input{display:none}@media(max-width:700px){aside{width:110px;padding:12px 6px}.brand{font-size:14px}main{padding:14px}.gallery{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}}
</style>
