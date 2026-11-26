<script setup lang="ts">
import {useWorkspace} from '../composables/useWorkspace'
import {zh,stageLabel,statusType} from '../labels'
const {error,reviews,state,imageUrl}=useWorkspace()
</script>
<template>
<div class="view-content"><el-table :data="reviews"><el-table-column label="素材" width="100"><template #default="s"><img class="thumb" :src="imageUrl(s.row.image_sha)"/></template></el-table-column><el-table-column label="状态" min-width="130"><template #default="s"><el-tag :type="statusType(s.row.state)">{{zh(s.row.state)}}</el-tag></template></el-table-column><el-table-column prop="backup_model" label="复核模型"/><el-table-column label="异常或分歧"><template #default="s">{{s.row.detail.error?zh(s.row.detail.error):(s.row.detail.differences?.map(zh).join('、')||'—')}}</template></el-table-column></el-table><p class="muted">显示前100条复核记录，暂不支持人工修改。</p></div>
</template>
