<script setup lang="ts">
import {useWorkspace} from '../composables/useWorkspace'
import {zh,stageLabel,statusType} from '../labels'
const {collection,saveCollection}=useWorkspace()
</script>
<template>
<div class="view-content"><div class="panel" v-for="t in collection" :key="t.id"><h3>{{zh(t.platform)}} / {{t.id}}</h3><div class="collection-fields"><div class="collection-field"><label>启用状态</label><el-switch v-model="t.enabled" active-text="启用" inactive-text="停用"/></div><div class="collection-field"><label>采集关键词</label><el-input v-model="t.keyword" placeholder="导入任务不按关键词搜索"/></div><div class="collection-field"><label>单次采集数量</label><el-input-number v-model="t.limit" :min="1" :max="20"/></div><div class="collection-field"><label>执行周期（小时）</label><el-input-number v-model="t.interval_hours" :min="1" :max="8760"/></div></div></div><el-button type="primary" @click="saveCollection">保存配置</el-button><p>仅修改已有任务；采集需在 production.json 启用 collect。</p></div>
</template>
