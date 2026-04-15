<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-gray-800">上传 DXF 文件</h2>
      <button @click="showHelp = !showHelp" class="text-primary hover:underline">
        {{ showHelp ? '隐藏帮助' : '查看帮助' }}
      </button>
    </div>

    <!-- 帮助信息 -->
    <div v-if="showHelp" class="bg-blue-50 border-l-4 border-primary p-4 rounded">
      <h3 class="font-semibold mb-2">使用说明：</h3>
      <ul class="list-disc list-inside space-y-1 text-gray-700">
        <li>支持 DXF R12-R2018 格式</li>
        <li>可识别的几何特征：外圆、锥面、圆弧、槽、螺纹</li>
        <li>支持批量上传多个 DXF 文件</li>
        <li>文件大小限制：50MB</li>
        <li>建议：零件轮廓应连续，起点 Z=0，向负 Z 方向延伸</li>
      </ul>
    </div>

    <!-- 拖拽上传区域 -->
    <div 
      class="drop-zone rounded-lg p-12 text-center cursor-pointer bg-white"
      :class="{ 'active': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="$refs.fileInput.click()"
    >
      <input 
        ref="fileInput" 
        type="file" 
        accept=".dxf" 
        multiple 
        class="hidden"
        @change="handleFileSelect"
      />
      
      <div class="space-y-4">
        <svg class="w-16 h-16 mx-auto text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
        </svg>
        <div>
          <p class="text-lg font-medium">点击或拖拽上传 DXF 文件</p>
          <p class="text-gray-500 text-sm mt-1">支持批量上传，每个文件最大 50MB</p>
        </div>
      </div>
    </div>

    <!-- 文件列表 -->
    <div v-if="selectedFiles.length > 0" class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">待处理文件 ({{ selectedFiles.length }})</h3>
      <div class="space-y-2 max-h-64 overflow-y-auto">
        <div v-for="(file, index) in selectedFiles" :key="index" class="flex items-center justify-between p-3 bg-gray-50 rounded">
          <div class="flex items-center space-x-3">
            <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            <span>{{ file.name }}</span>
            <span class="text-sm text-gray-500">({{ formatFileSize(file.size) }})</span>
          </div>
          <button @click="removeFile(index)" class="text-danger hover:text-red-700">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>
      
      <div class="mt-4 flex justify-end space-x-3">
        <button @click="selectedFiles = []" class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">
          清空
        </button>
        <button 
          @click="startUpload" 
          :disabled="isUploading"
          class="px-6 py-2 bg-primary text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ isUploading ? '上传中...' : '开始处理' }}
        </button>
      </div>
    </div>

    <!-- 加工参数配置 -->
    <div v-if="selectedFiles.length > 0" class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">加工参数配置</h3>
      <div class="grid md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">材料</label>
          <select v-model="config.material" class="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="45#钢">45#钢</option>
            <option value="40Cr">40Cr</option>
            <option value="不锈钢">不锈钢</option>
            <option value="铝合金">铝合金</option>
            <option value="黄铜">黄铜</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">数控系统</label>
          <select v-model="config.machineSystem" class="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="FANUC">FANUC</option>
            <option value="Siemens">Siemens</option>
            <option value="Mitsubishi">Mitsubishi</option>
            <option value="GSK">GSK</option>
            <option value="HNC">HNC</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">保存选项</label>
          <select v-model="config.saveOption" class="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="auto">自动生成并保存</option>
            <option value="preview">仅预览不保存</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 进度显示 -->
    <div v-if="uploadProgress.total > 0" class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">处理进度</h3>
      <div class="space-y-4">
        <div class="bg-gray-200 rounded-full h-4">
          <div 
            class="bg-primary h-4 rounded-full progress-bar transition-all duration-300"
            :style="{ width: uploadProgress.percent + '%' }"
          ></div>
        </div>
        <div class="flex justify-between text-sm text-gray-600">
          <span>{{ uploadProgress.current }} / {{ uploadProgress.total }}</span>
          <span>{{ uploadProgress.percent }}%</span>
        </div>
        
        <!-- 详细状态 -->
        <div class="max-h-48 overflow-y-auto space-y-2">
          <div v-for="(status, idx) in uploadStatuses" :key="idx" 
               class="flex items-center justify-between p-2 rounded"
               :class="{
                 'bg-green-50 text-green-700': status.status === 'success',
                 'bg-red-50 text-red-700': status.status === 'error',
                 'bg-blue-50 text-blue-700': status.status === 'processing',
                 'bg-gray-50 text-gray-700': status.status === 'pending'
               }">
            <span>{{ status.filename }}</span>
            <span class="text-sm">
              {{ statusMessage(status) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- DXF 预览 -->
    <div v-if="previewData" class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">几何预览</h3>
      <canvas ref="previewCanvas" width="600" height="400" class="border rounded canvas-container mx-auto"></canvas>
      <div class="mt-4 grid md:grid-cols-2 gap-4">
        <div>
          <h4 class="font-medium mb-2">识别的特征</h4>
          <ul class="space-y-1">
            <li v-for="(feature, idx) in previewData.features" :key="idx" class="text-sm">
              <span class="inline-block w-20 text-gray-600">{{ feature.type }}:</span>
              <span>{{ formatFeature(feature) }}</span>
            </li>
          </ul>
        </div>
        <div>
          <h4 class="font-medium mb-2">几何统计</h4>
          <div class="text-sm space-y-1">
            <div>实体总数：{{ previewData.entityCount }}</div>
            <div>最大直径：{{ previewData.maxDiameter }} mm</div>
            <div>总长度：{{ previewData.totalLength }} mm</div>
          </div>
        </div>
      </div>
    </div>

    <!-- G 代码预览 -->
    <div v-if="generatedGCode" class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold">生成的 G 代码</h3>
        <div class="space-x-2">
          <button @click="copyGCode" class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded">
            复制
          </button>
          <button @click="downloadGCode" class="px-3 py-1 text-sm bg-primary text-white hover:bg-blue-600 rounded">
            下载
          </button>
        </div>
      </div>
      <div class="bg-gray-900 rounded-lg p-4 overflow-x-auto max-h-96 overflow-y-auto">
        <pre><code v-html="highlightedGCode"></code></pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const showHelp = ref(false)
const isDragging = ref(false)
const selectedFiles = ref([])
const isUploading = ref(false)
const uploadProgress = ref({ total: 0, current: 0, percent: 0 })
const uploadStatuses = ref([])
const previewData = ref(null)
const generatedGCode = ref(null)
const previewCanvas = ref(null)

const config = ref({
  material: '45#钢',
  machineSystem: 'FANUC',
  saveOption: 'auto',
})

// 文件处理函数
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  selectedFiles.value.push(...files)
}

const handleDrop = (event) => {
  isDragging.value = false
  const files = Array.from(event.dataTransfer.files).filter(f => f.name.endsWith('.dxf'))
  selectedFiles.value.push(...files)
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 批量上传
const startUpload = async () => {
  if (selectedFiles.value.length === 0) return
  
  isUploading.value = true
  uploadProgress.value = { total: selectedFiles.value.length, current: 0, percent: 0 }
  uploadStatuses.value = selectedFiles.value.map(f => ({ filename: f.name, status: 'pending' }))
  
  for (let i = 0; i < selectedFiles.value.length; i++) {
    const file = selectedFiles.value[i]
    updateStatus(i, 'processing')
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('material', config.value.material)
      formData.append('machine_system', config.value.machineSystem)
      
      const response = await axios.post('/api/gcode/upload-dxf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      
      updateStatus(i, 'success', response.data)
      
      // 更新预览
      if (response.data.gcode && response.data.features) {
        previewData.value = {
          features: response.data.features,
          entityCount: response.data.entity_count || 0,
          maxDiameter: response.data.stock_diameter || 0,
          totalLength: response.data.total_length || 0,
        }
        generatedGCode.value = response.data.gcode
        drawDXFPreview(response.data.entities || [])
      }
      
    } catch (error) {
      updateStatus(i, 'error', error.message)
    }
    
    uploadProgress.value.current = i + 1
    uploadProgress.value.percent = Math.round((i + 1) / selectedFiles.value.length * 100)
  }
  
  isUploading.value = false
}

const updateStatus = (index, status, data = null) => {
  uploadStatuses.value[index] = {
    ...uploadStatuses.value[index],
    status,
    data,
  }
}

const statusMessage = (status) => {
  switch (status.status) {
    case 'pending': return '等待中...'
    case 'processing': return '处理中...'
    case 'success': return '✓ 完成'
    case 'error': return `✗ ${status.data}`
    default: return ''
  }
}

// DXF 预览绘制
const drawDXFPreview = (entities) => {
  if (!previewCanvas.value || entities.length === 0) return
  
  const canvas = previewCanvas.value
  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height
  
  // 清空画布
  ctx.clearRect(0, 0, width, height)
  
  // 计算边界
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity
  entities.forEach(e => {
    if (e.type === 'LINE') {
      minX = Math.min(minX, e.start.x, e.end.x)
      maxX = Math.max(maxX, e.start.x, e.end.x)
      minZ = Math.min(minZ, e.start.z, e.end.z)
      maxZ = Math.max(maxZ, e.start.z, e.end.z)
    }
  })
  
  // 计算缩放和平移
  const padding = 40
  const scaleX = (width - padding * 2) / (maxX - minX || 1)
  const scaleZ = (height - padding * 2) / (maxZ - minZ || 1)
  const scale = Math.min(scaleX, scaleZ) * 0.9
  const offsetX = padding - minX * scale + (width - padding) / 2
  const offsetZ = height - padding - minZ * scale
  
  // 绘制坐标轴
  ctx.strokeStyle = '#ccc'
  ctx.beginPath()
  ctx.moveTo(offsetX, 0)
  ctx.lineTo(offsetX, height)
  ctx.moveTo(0, offsetZ)
  ctx.lineTo(width, offsetZ)
  ctx.stroke()
  
  // 绘制实体
  ctx.strokeStyle = '#3B82F6'
  ctx.lineWidth = 2
  entities.forEach(e => {
    ctx.beginPath()
    if (e.type === 'LINE') {
      const x1 = offsetX + e.start.x * scale
      const z1 = offsetZ - e.start.z * scale
      const x2 = offsetX + e.end.x * scale
      const z2 = offsetZ - e.end.z * scale
      ctx.moveTo(x1, z1)
      ctx.lineTo(x2, z2)
    } else if (e.type === 'CIRCLE') {
      const x = offsetX + e.center.x * scale
      const z = offsetZ - e.center.z * scale
      const r = e.radius * scale
      ctx.arc(x, z, r, 0, Math.PI * 2)
    }
    ctx.stroke()
  })
}

// G 代码高亮
const highlightedGCode = computed(() => {
  if (!generatedGCode.value) return ''
  
  let code = generatedGCode.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  
  // 按顺序应用高亮规则
  code = code
    .replace(/\(.*?\)|;[^\n]*/g, '<span class="gcode-comment">$&</span>')
    .replace(/O\d+/g, '<span class="gcode-program">$&</span>')
    .replace(/G\d+/g, '<span class="gcode-gcode">$&</span>')
    .replace(/M\d+/g, '<span class="gcode-mcode">$&</span>')
    .replace(/T\d+/g, '<span class="gcode-tcode">$&</span>')
    .replace(/S\d+/g, '<span class="gcode-scode">$&</span>')
    .replace(/F\d+/g, '<span class="gcode-fcode">$&</span>')
    .replace(/[XZIK][-+]?\d*\.?\d+/g, '<span class="gcode-coord">$&</span>')
  
  return code
})

// 辅助函数
const formatFeature = (feature) => {
  if (feature.type === 'external_cylinder') {
    return `直径 ${feature.diameter}mm, 长度 ${feature.length}mm`
  } else if (feature.type === 'taper') {
    return `起始直径 ${feature.start_diameter}mm, 终止直径 ${feature.end_diameter}mm`
  } else if (feature.type === 'groove') {
    return `宽度 ${feature.width}mm, 深度 ${feature.depth}mm`
  } else if (feature.type === 'thread') {
    return `规格 ${feature.spec}`
  }
  return JSON.stringify(feature)
}

const copyGCode = () => {
  navigator.clipboard.writeText(generatedGCode.value)
  alert('已复制到剪贴板')
}

const downloadGCode = () => {
  const blob = new Blob([generatedGCode.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `program_${Date.now()}.nc`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
