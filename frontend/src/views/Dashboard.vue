<script setup lang="ts">
import {useWorkspace} from '../composables/useWorkspace'
import {zh,stageLabel,statusType} from '../labels'
const {stats,names}=useWorkspace()
</script>
<template>
<div class="view-content"><p class="muted">本地素材库实时统计</p><div class="metrics"><div class="panel" v-for="(v,k) in stats" :key="k"><small>{{names[k]||k}}</small><strong>{{v}}</strong></div></div><div class="panel"><h3>数据生产流程</h3><div class="process">采集 → 抽帧 → 聚类 → 标签 → 复核 → 推荐 → 归档</div></div></div>
</template>
