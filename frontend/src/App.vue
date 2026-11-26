<script setup lang="ts">
import {ref,onMounted} from 'vue'
type Item={image_sha:string;status?:string;score?:number;tags?:Record<string,any>}
const pages=['数据总览','素材管理','智能检索','标签管理','AI审核中心','任务管理']
const page=ref('数据总览'),busy=ref(false),error=ref('')
const stats=ref<Record<string,number>>({}),items=ref<Item[]>([]),reviews=ref<any[]>([]),runs=ref<any[]>([]),steps=ref<any[]>([])
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
 if(page.value==='数据总览') stats.value=await request('/statistics')
 else if(page.value==='素材管理'){const r=await request('/assets?'+new URLSearchParams({limit:'24',offset:String((current.value-1)*24),state:state.value}));items.value=r.items;total.value=r.total}
 else if(page.value==='AI审核中心') reviews.value=await request('/reviews')
 else if(page.value==='任务管理'){const r=await request('/pipeline');runs.value=r.runs;steps.value=r.steps}
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
 <div class="gallery"><article v-for="item in items" :key="item.image_sha" @click="selected=item"><img :src="imageUrl(item.image_sha)" loading="lazy" alt="美甲素材"/><div class="meta"><el-tag size="small" v-if="item.status">{{item.status}}</el-tag><small v-if="item.score!==undefined">得分 {{item.score.toFixed(3)}}</small><p>{{item.tags?.description||item.image_sha.slice(0,12)}}</p><el-tag v-for="tag in [...(item.tags?.colors||[]),...(item.tags?.styles||[])]" :key="tag" size="small" effect="plain">{{tag}}</el-tag></div></article></div>
 <el-empty v-if="!items.length" description="暂无匹配素材"/>
 <el-pagination v-if="page==='素材管理'" v-model:current-page="current" :page-size="24" :total="total" layout="prev,pager,next" @current-change="load"/>
 </template>
 <template v-if="page==='标签管理'"><div class="panel" v-for="group in [{name:'颜色',values:colors},{name:'款式',values:styles},{name:'甲型',values:shapes}]" :key="group.name"><h3>{{group.name}}</h3><el-tag v-for="x in group.values" :key="x" effect="plain">{{x}}</el-tag></div><p class="muted">当前为标签字典浏览，编辑功能尚未开放。</p></template>
 <template v-if="page==='AI审核中心'"><el-table :data="reviews"><el-table-column label="素材" width="100"><template #default="s"><img class="thumb" :src="imageUrl(s.row.image_sha)"/></template></el-table-column><el-table-column prop="state" label="状态"/><el-table-column prop="backup_model" label="复核模型"/><el-table-column label="异常或分歧"><template #default="s">{{s.row.detail.error||s.row.detail.differences?.join('、')||'—'}}</template></el-table-column></el-table><p class="muted">显示前100条复核记录，暂不支持人工修改。</p></template>
 <template v-if="page==='任务管理'"><h3>最近运行</h3><el-table :data="runs"><el-table-column prop="id" label="运行ID"/><el-table-column prop="state" label="状态"/></el-table><h3>最新运行阶段</h3><el-table :data="steps"><el-table-column prop="name" label="阶段"/><el-table-column prop="state" label="状态"/><el-table-column prop="seconds" label="耗时（秒）"/><el-table-column prop="payload" label="结果" show-overflow-tooltip/></el-table></template>
 </section></main>
 <el-dialog :model-value="!!selected" title="素材详情" width="min(720px,90vw)" @close="selected=null"><template v-if="selected"><img class="detail" :src="imageUrl(selected.image_sha)"/><pre>{{JSON.stringify(selected.tags,null,2)}}</pre></template></el-dialog>
 </div>
</template>
<style>
*{box-sizing:border-box}body{margin:0;background:#f7f6f8;color:#292432;font:14px system-ui,sans-serif}.shell{display:flex;min-height:100vh}aside{width:220px;flex-shrink:0;background:#282334;color:#fff;padding:28px 16px;position:sticky;top:0;height:100vh}.brand{font-size:23px;font-weight:800;letter-spacing:1px;margin:0 8px 36px}.brand span{color:#dca7c5}.brand small{display:block;font-size:12px;color:#c6bdce;margin-top:8px;font-weight:400}aside button{display:block;width:100%;text-align:left;border:0;background:transparent;color:#d8d0df;padding:14px 16px;border-radius:8px;margin:4px 0;cursor:pointer}aside button.active{background:#514057;color:white}footer{position:absolute;bottom:24px;font-size:10px;letter-spacing:2px;color:#a99bb2}main{flex:1;min-width:0;padding:30px;max-width:1600px}header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}header small,.muted{color:#817989}h1{font-size:28px;margin:8px 0}h3{margin-top:0}.panel{background:white;border:1px solid #ebe7ee;border-radius:12px;padding:20px;margin-bottom:18px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px}.metrics strong{display:block;font-size:34px;margin-top:14px}.process{line-height:2;color:#72536f}.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.toolbar .el-input{flex:1;min-width:220px}.toolbar .el-select{width:130px}.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px;margin:20px 0}.gallery article{background:white;border:1px solid #ebe7ee;border-radius:12px;overflow:hidden;cursor:pointer}.gallery img{width:100%;aspect-ratio:1;object-fit:cover;display:block}.meta{padding:12px}.meta p{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.el-tag{margin:3px}.thumb{width:64px;height:64px;object-fit:cover;border-radius:6px}.detail{max-width:100%;max-height:400px;display:block;margin:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}.upload{cursor:pointer;border:1px solid #dcdfe6;border-radius:5px;padding:8px 14px;background:white}.upload input{display:none}@media(max-width:700px){aside{width:110px;padding:12px 6px}.brand{font-size:14px}main{padding:14px}.gallery{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}}
</style>
