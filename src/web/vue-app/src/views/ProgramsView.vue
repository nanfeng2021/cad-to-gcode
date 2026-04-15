<template>
  <div class="space-y-6">
    <!-- 标题和搜索 -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-gray-800">程序管理</h2>
      <div class="relative">
        <input 
          v-model="searchQuery"
          type="text" 
          placeholder="搜索程序..."
          class="border rounded-lg px-4 py-2 pl-10 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <svg class="w-5 h-5 absolute left-3 top-2.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
        </svg>
      </div>
    </div>

    <!-- 筛选器 -->
    <div class="flex space-x-4 bg-white p-4 rounded-lg shadow">
      <select v-model="filterMaterial" class="border rounded px-3 py-2">
        <option value="">全部材料</option>
        <option value="45#钢">45#钢</option>
        <option value="40Cr">40Cr</option>
        <option value="不锈钢">不锈钢</option>
        <option value="铝合金">铝合金</option>
        <option value="黄铜">黄铜</option>
      </select>
      
      <select v-model="filterMachine" class="border rounded px-3 py-2">
        <option value="">全部系统</option>
        <option value="FANUC">FANUC</option>
        <option value="Siemens">Siemens</option>
        <option value="Mitsubishi">Mitsubishi</option>
        <option value="GSK">GSK</option>
        <option value="HNC">HNC</option>
      </select>
      
      <button @click="loadPrograms" class="px-4 py-2 bg-primary text-white rounded hover:bg-blue-600">
        刷新
      </button>
    </div>

    <!-- 程序列表 -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">文件名</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">材料</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">数控系统</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="program in filteredPrograms" :key="program.id" class="hover:bg-gray-50 cursor-pointer" @click="viewProgram(program)">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="font-medium text-primary">{{ program.filename }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ program.material }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ program.machine_system }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDate(program.created_at) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button @click.stop="viewProgram(program)" class="text-primary hover:text-blue-700 mr-3">查看</button>
              <button @click.stop="deleteProgram(program.id, program.filename)" class="text-danger hover:text-red-700">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <div v-if="filteredPrograms.length === 0" class="text-center py-12 text-gray-500">
        暂无程序
      </div>
    </div>

    <!-- G 代码查看对话框 -->
    <div v-if="selectedProgram" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold">{{ selectedProgram.filename }}</h3>
          <button @click="selectedProgram = null" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        <div class="p-4 overflow-auto max-h-[60vh]">
          <div class="bg-gray-900 rounded-lg p-4">
            <pre><code v-html="highlightGCode(selectedProgram.content)"></code></pre>
          </div>
        </div>
        
        <div class="p-4 border-t flex justify-end space-x-3">
          <button @click="copyGCode(selectedProgram.content)" class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded">复制</button>
          <button @click="downloadProgram(selectedProgram)" class="px-4 py-2 bg-primary text-white rounded hover:bg-blue-600">下载</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const searchQuery = ref('')
const filterMaterial = ref('')
const filterMachine = ref('')
const programs = ref([])
const selectedProgram = ref(null)

onMounted(async () => {
  await loadPrograms()
})

const loadPrograms = async () => {
  try {
    const response = await axios.get('/api/programs')
    programs.value = response.data
  } catch (error) {
    console.error('加载程序列表失败:', error)
  }
}

const filteredPrograms = computed(() => {
  return programs.value.filter(p => {
    const matchSearch = !searchQuery.value || 
      p.filename.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (p.material && p.material.toLowerCase().includes(searchQuery.value.toLowerCase()))
    
    const matchMaterial = !filterMaterial.value || p.material === filterMaterial.value
    const matchMachine = !filterMachine.value || p.machine_system === filterMachine.value
    
    return matchSearch && matchMaterial && matchMachine
  })
})

const viewProgram = async (program) => {
  selectedProgram = { ...program }
}

const deleteProgram = async (id, filename) => {
  if (!confirm(`确定要删除 "${filename}" 吗？此操作不可恢复。`)) return
  
  try {
    await axios.delete(`/api/programs/${id}`)
    await loadPrograms()
  } catch (error) {
    alert('删除失败：' + error.message)
  }
}

const highlightGCode = (gcode) => {
  let code = gcode
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  
  code = code
    .replace(/\(.*?\)|;[^\n]*/g, '<span class="gcode-comment">$&</span>')
    .replace(/O\d+/g, '<span class="gcode-program">$&</span>')
    .replace(/G\d+/g, '<span class="gcode-gcode">$&</span>')
    .replace(/M\d+/g, '<span class="gcode-mcode">$&</span>')
    .replace(/[XZIK][-+]?\d*\.?\d+/g, '<span class="gcode-coord">$&</span>')
  
  return code
}

const copyGCode = (content) => {
  navigator.clipboard.writeText(content)
  alert('已复制到剪贴板')
}

const downloadProgram = (program) => {
  const blob = new Blob([program.content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = program.filename
  a.click()
  URL.revokeObjectURL(url)
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}
</script>
