<script setup lang="ts">
import {useWorkspace} from '../composables/useWorkspace'
import {zh,stageLabel,statusType} from '../labels'
const {page,items,openItem,total,current,state,q,color,style,shape,include,colors,styles,shapes,imageUrl,load,search,upload}=useWorkspace()
</script>
<template>
<div class="view-content">
 <div class="panel toolbar" v-if="page==='素材管理'"><el-select v-model="state" placeholder="全部状态" clearable @change="current=1;load()"><el-option label="成功" value="success"/><el-option label="待审核" value="review"/><el-option label="失败" value="failed"/></el-select><span>共 {{total}} 张</span></div>
 <div class="panel toolbar" v-else><el-input v-model="q" placeholder="输入中英文描述，例如 裸粉色猫眼美甲" @keyup.enter="search"/><el-select v-model="color" placeholder="颜色" clearable><el-option v-for="x in colors" :key="x" :value="x"/></el-select><el-select v-model="style" placeholder="款式" clearable><el-option v-for="x in styles" :key="x" :value="x"/></el-select><el-select v-model="shape" placeholder="甲型" clearable><el-option v-for="x in shapes" :key="x" :value="x"/></el-select><el-checkbox v-model="include">包含未审核</el-checkbox><el-button type="primary" @click="search">搜索</el-button><label class="upload">上传图片<input type="file" accept="image/jpeg,image/png,image/webp" @change="upload"/></label></div>
 <div class="gallery"><article v-for="item in items" :key="item.image_sha" @click="openItem(item)"><img :src="imageUrl(item.image_sha)" loading="lazy" alt="美甲素材"/><div class="meta"><el-tag size="small" v-if="item.status" :type="statusType(item.status)">{{zh(item.status)}}</el-tag><small v-if="item.score!==undefined">得分 {{item.score.toFixed(3)}}</small><p>{{item.tags?.description||item.image_sha.slice(0,12)}}</p><el-tag v-for="tag in [...(item.tags?.colors||[]),...(item.tags?.styles||[])]" :key="tag" size="small" effect="plain">{{tag}}</el-tag></div></article></div>
 <el-empty v-if="!items.length" description="暂无匹配素材"/>
 <el-pagination v-if="page==='素材管理'" v-model:current-page="current" :page-size="24" :total="total" layout="prev,pager,next" @current-change="load"/>
 </div>
</template>
