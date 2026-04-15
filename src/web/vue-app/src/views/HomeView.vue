<template>
  <div class="space-y-8">
    <!-- 欢迎横幅 -->
    <div class="bg-gradient-to-r from-primary to-blue-600 rounded-lg shadow-lg p-8 text-white">
      <h2 class="text-3xl font-bold mb-4">CAD to G-code Platform</h2>
      <p class="text-lg opacity-90 mb-6">
        AI 驱动的 2 轴数控车床 G 代码自动生成系统
      </p>
      <div class="flex space-x-4">
        <router-link to="/upload" class="bg-white text-primary px-6 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">
          开始上传 DXF
        </router-link>
        <router-link to="/programs" class="border border-white text-white px-6 py-3 rounded-lg font-semibold hover:bg-white hover:text-primary transition">
          查看程序库
        </router-link>
      </div>
    </div>

    <!-- 功能特性 -->
    <div class="grid md:grid-cols-3 gap-6">
      <div class="bg-white rounded-lg shadow p-6 card-hover">
        <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
          <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
          </svg>
        </div>
        <h3 class="text-xl font-semibold mb-2">智能解析</h3>
        <p class="text-gray-600">自动识别 DXF 文件中的几何特征，包括外圆、锥面、圆弧、槽和螺纹</p>
      </div>

      <div class="bg-white rounded-lg shadow p-6 card-hover">
        <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
          <svg class="w-6 h-6 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
        </div>
        <h3 class="text-xl font-semibold mb-2">工艺规划</h3>
        <p class="text-gray-600">基于材料、工序和数控系统自动推荐切削参数，支持 7 种材料和 5 种数控系统</p>
      </div>

      <div class="bg-white rounded-lg shadow p-6 card-hover">
        <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
          <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
        </div>
        <h3 class="text-xl font-semibold mb-2">多系统支持</h3>
        <p class="text-gray-600">生成 FANUC、Siemens、Mitsubishi、GSK、HNC 等多种数控系统的 G 代码</p>
      </div>
    </div>

    <!-- 快速统计 -->
    <div class="grid md:grid-cols-4 gap-4">
      <div class="bg-white rounded-lg shadow p-4 text-center">
        <div class="text-3xl font-bold text-primary">{{ stats.programCount }}</div>
        <div class="text-gray-600 mt-1">已生成程序</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4 text-center">
        <div class="text-3xl font-bold text-secondary">{{ stats.materialCount }}</div>
        <div class="text-gray-600 mt-1">支持材料</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4 text-center">
        <div class="text-3xl font-bold text-warning">{{ stats.machineCount }}</div>
        <div class="text-gray-600 mt-1">数控系统</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4 text-center">
        <div class="text-3xl font-bold text-purple-600">{{ stats.featureCount }}</div>
        <div class="text-gray-600 mt-1">识别特征</div>
      </div>
    </div>

    <!-- 最近活动 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-xl font-semibold mb-4">最近生成的程序</h3>
      <div v-if="recentPrograms.length > 0" class="space-y-3">
        <div v-for="program in recentPrograms" :key="program.id" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div>
            <div class="font-medium">{{ program.filename }}</div>
            <div class="text-sm text-gray-500">{{ program.material }} • {{ program.machine_system }}</div>
          </div>
          <div class="text-sm text-gray-400">{{ formatDate(program.created_at) }}</div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-500">
        暂无程序，上传第一个 DXF 文件开始使用
      </div>
      <div class="mt-4 text-center">
        <router-link to="/programs" class="text-primary hover:underline">查看全部 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const stats = ref({
  programCount: 0,
  materialCount: 7,
  machineCount: 5,
  featureCount: 7,
})

const recentPrograms = ref([])

onMounted(async () => {
  try {
    const response = await axios.get('/api/programs')
    recentPrograms.value = response.data.slice(0, 5)
    stats.value.programCount = response.data.length
  } catch (error) {
    console.error('加载程序列表失败:', error)
  }
})

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>
