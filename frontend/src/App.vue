<script setup lang="ts">
import {onMounted} from 'vue'
import {useWorkspace} from './composables/useWorkspace'
import Dashboard from './views/Dashboard.vue'
import Assets from './views/Assets.vue'
import Search from './views/Search.vue'
import Tags from './views/Tags.vue'
import Review from './views/Review.vue'
import Tasks from './views/Tasks.vue'
import Collection from './views/Collection.vue'
import AssetDialog from './components/AssetDialog.vue'
import './styles/workspace.css'
const {page,pages,busy,error,navigate,search,load}=useWorkspace()
onMounted(load)
</script>
<template>
<div class="shell"><aside><div class="brand">NAIL<span>MEDIA AI</span><small>美甲素材工作台</small></div><button v-for="p in pages" :key="p" :class="{active:page===p}" @click="navigate(p)">{{p}}</button><footer>本地工作空间</footer></aside><main><header><div><small>素材生产与检索 / {{page}}</small><h1>{{page}}</h1></div><el-button :loading="busy" @click="page==='智能检索'?search():load()">刷新</el-button></header><el-alert v-if="error" :title="error" type="error" show-icon :closable="false"/><section v-loading="busy"><Dashboard v-if="page==='数据总览'"/><Assets v-else-if="page==='素材管理'"/><Search v-else-if="page==='智能检索'"/><Tags v-else-if="page==='标签管理'"/><Review v-else-if="page==='AI审核中心'"/><Tasks v-else-if="page==='任务管理'"/><Collection v-else-if="page==='采集配置'"/></section></main><AssetDialog/></div>
</template>