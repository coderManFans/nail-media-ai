import {ref} from 'vue'
import {ElMessageBox,ElMessage} from 'element-plus'
type Item={image_sha:string;status?:string;score?:number;tags?:Record<string,any>}
const pages=['数据总览','素材管理','智能检索','标签管理','AI审核中心','任务管理','采集配置']
const page=ref('数据总览'),busy=ref(false),error=ref('')
const stats=ref<Record<string,number>>({}),items=ref<Item[]>([]),reviews=ref<any[]>([]),runs=ref<any[]>([]),steps=ref<any[]>([])
type DictTag={category:string;code:string;label:string;enabled:boolean|number;builtin:boolean|number}
const dictionary=ref<DictTag[]>([])
const dictGroups=[{name:'颜色',category:'colors'},{name:'款式',category:'styles'},{name:'甲型',category:'nail_shape'}]
const dictDraft=ref({category:'colors',code:'',label:'',enabled:true,operation:'create'})
const dictOpen=ref(false),dictCategory=ref('colors')
function editTag(category:string,t?:DictTag){dictDraft.value={category,code:t?.code||'',label:t?.label||'',enabled:t?!!t.enabled:true,operation:t?'update':'create'};dictOpen.value=true}
async function saveTag(){await action(async()=>{const d=dictDraft.value;dictionary.value=await request('/tag-dictionary',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...d,code:d.operation==='create'?d.label.trim():d.code})});dictOpen.value=false;ElMessage.success('保存成功')})}
async function deleteTag(t:DictTag){try{await ElMessageBox.confirm(t.builtin?'内置标签将停用，保留历史识别值。':'确认删除自定义标签？','确认操作')}catch{return}await action(async()=>{dictionary.value=await request('/tag-dictionary',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({category:t.category,code:t.code,operation:'delete'})});ElMessage.success('操作成功')})}
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
 if(page.value==='标签管理') dictionary.value=await request('/tag-dictionary')
 else if(page.value==='采集配置') collection.value=await request('/collection')
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
export function useWorkspace(){return {page,busy,error,stats,items,reviews,runs,steps,dictionary,dictGroups,dictDraft,dictOpen,dictCategory,editTag,saveTag,deleteTag,collection,authorized,schema,formTags,advanced,saveCollection,job,kind,jobLimit,draft,refreshJob,startJob,openItem,saveReview,total,current,state,q,color,style,shape,include,selected,names,colors,styles,shapes,imageUrl,load,navigate,search,upload,pages}}
