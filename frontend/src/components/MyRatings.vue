<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface RatingItem {
  title: string
  year: number | null
  genres: string | null
  rating: number | null
  review: string | null
  tagged_date: string | null
  imdb_id: string | null
  source_url: string | null
}

const ratings = ref<RatingItem[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(0)
const pageSize = 20
const searchQuery = ref('')
const minRating = ref<number | null>(null)
const sortBy = ref<string>('created_at')

// Import
const uploading = ref(false)
const importResult = ref<any>(null)

// Edit state
const editingId = ref<string | null>(null)
const editRating = ref(0)
const editReview = ref('')

async function loadRatings() {
  loading.value = true
  try {
    let url = `/api/ratings?user_id=default&limit=${pageSize}&offset=${page.value * pageSize}&sort=${sortBy.value}`
    if (minRating.value) url += `&min_rating=${minRating.value}`
    if (searchQuery.value.trim()) url += `&search=${encodeURIComponent(searchQuery.value.trim())}`
    const res = await fetch(url)
    const data = await res.json()
    ratings.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function setFilter(rating: number | null) {
  minRating.value = rating
  page.value = 0
  loadRatings()
}

function setSort(s: string) {
  sortBy.value = s
  page.value = 0
  loadRatings()
}

function doSearch() {
  page.value = 0
  loadRatings()
}

async function handleUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  importResult.value = null
  const form = new FormData()
  form.append('file', file)
  form.append('user_id', 'default')
  try {
    const res = await fetch('/api/ratings/import', { method: 'POST', body: form })
    importResult.value = await res.json()
    await loadRatings()
  } catch (err: any) {
    importResult.value = { error: err.message }
  } finally {
    uploading.value = false
  }
}

async function handleDelete(imdbId: string) {
  if (!confirm('删除这条评分？')) return
  await fetch(`/api/ratings/${imdbId}?user_id=default`, { method: 'DELETE' })
  loadRatings()
}

function startEdit(item: RatingItem) {
  editingId.value = item.imdb_id
  editRating.value = Math.round(item.rating || 0)
  editReview.value = item.review || ''
}

async function saveEdit() {
  if (!editingId.value) return
  const params = new URLSearchParams({ user_id: 'default', rating: String(editRating.value), review: editReview.value })
  await fetch(`/api/ratings/${editingId.value}?${params}`, { method: 'PUT' })
  editingId.value = null
  loadRatings()
}

function cancelEdit() { editingId.value = null }

function prevPage() { if (page.value > 0) { page.value--; loadRatings() } }
function nextPage() { if ((page.value + 1) * pageSize < total.value) { page.value++; loadRatings() } }

function starColor(r: number | null): string {
  if (!r) return 'var(--text-muted)'
  return r >= 4 ? '#22C55E' : r >= 3 ? 'var(--accent)' : 'var(--danger)'
}

onMounted(loadRatings)
</script>

<template>
  <div class="ratings-page">
    <!-- Upload Section -->
    <section class="upload-section">
      <label class="upload-btn" :class="{ disabled: uploading }">
        {{ uploading ? '导入中...' : '📂 上传豆瓣 CSV' }}
        <input type="file" accept=".csv" @change="handleUpload" :disabled="uploading" hidden />
      </label>
      <div v-if="importResult" class="import-result">
        <template v-if="importResult.error">
          <span class="error">{{ importResult.error }}</span>
        </template>
        <template v-else>
          <span class="stat">总 <b>{{ importResult.total }}</b></span>
          <span class="stat">新电影 <b>{{ importResult.new_movies }}</b></span>
          <span class="stat">评分 <b>{{ importResult.new_ratings }}</b></span>
          <span class="stat">TMDB <b>{{ importResult.tmdb_enriched }}</b></span>
        </template>
      </div>
    </section>

    <!-- Filters + Sort -->
    <div class="toolbar">
      <div class="filters">
        <button :class="['fbtn', { active: minRating === null }]" @click="setFilter(null)">全部</button>
        <button v-for="n in 5" :key="n" :class="['fbtn', { active: minRating === n }]" @click="setFilter(n)">≥ {{ '★'.repeat(n) }}</button>
      </div>
      <div class="search-group">
        <input v-model="searchQuery" class="search-input" placeholder="搜索片名..." @keydown.enter="doSearch" />
        <button class="fbtn" @click="doSearch">搜索</button>
      </div>
      <div class="sort-group">
        <button :class="['fbtn', { active: sortBy === 'created_at' }]" @click="setSort('created_at')">最新</button>
        <button :class="['fbtn', { active: sortBy === 'rating' }]" @click="setSort('rating')">评分优先</button>
      </div>
    </div>

    <!-- List -->
    <section class="rating-list">
      <div class="list-header">
        <h3>我的评分 <span class="count">({{ total }})</span></h3>
        <div class="pager">
          <button @click="prevPage" :disabled="page === 0">←</button>
          <span>{{ page + 1 }} / {{ Math.ceil(total / pageSize) || 1 }}</span>
          <button @click="nextPage" :disabled="(page + 1) * pageSize >= total">→</button>
        </div>
      </div>

      <div v-if="loading" class="loading">加载中...</div>

      <div v-else class="cards">
        <div v-for="item in ratings" :key="item.imdb_id || item.title" class="card">
          <!-- Edit Mode -->
          <template v-if="editingId === item.imdb_id">
            <div class="edit-row">
              <span class="title">{{ item.title }}</span>
              <div class="edit-controls">
                <select v-model="editRating" class="edit-select">
                  <option v-for="n in 5" :key="n" :value="n">{{ '★'.repeat(n) }}</option>
                </select>
                <input v-model="editReview" placeholder="评价..." class="edit-input" @keydown.enter="saveEdit" />
                <button class="save-btn" @click="saveEdit">保存</button>
                <button class="cancel-btn" @click="cancelEdit">取消</button>
              </div>
            </div>
          </template>

          <!-- View Mode -->
          <template v-else>
            <div class="card-left">
              <a v-if="item.source_url" :href="item.source_url" target="_blank" class="title-link">{{ item.title }}</a>
              <span v-else class="title">{{ item.title }}</span>
              <span class="meta">
                {{ item.year || '未知' }}
                <template v-if="item.genres"> · {{ item.genres }}</template>
              </span>
              <span v-if="item.review" class="review">"{{ item.review }}"</span>
            </div>
            <div class="card-right">
              <span class="stars" :style="{ color: starColor(item.rating) }">
                {{ item.rating ? '★'.repeat(Math.round(item.rating)) + '☆'.repeat(5 - Math.round(item.rating)) : '—' }}
              </span>
              <span class="date">{{ item.tagged_date?.slice(0, 10) }}</span>
              <div class="actions">
                <button class="act-btn" @click="startEdit(item)">✎</button>
                <button class="act-btn del" @click="handleDelete(item.imdb_id!)">✕</button>
              </div>
            </div>
          </template>
        </div>
        <div v-if="ratings.length === 0 && !loading" class="empty">暂无评分</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ratings-page { flex: 1; height: 100vh; overflow-y: auto; display: flex; flex-direction: column; }
.upload-section { padding: 20px 24px; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
.upload-btn { display: inline-block; padding: 8px 18px; border: 1px solid var(--accent); color: var(--accent); border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 200ms; }
.upload-btn:hover { background: var(--accent); color: #121212; }
.upload-btn.disabled { opacity: 0.5; pointer-events: none; }
.import-result { display: flex; gap: 20px; margin-top: 12px; flex-wrap: wrap; }
.stat { font-size: 13px; color: var(--text-secondary); }
.stat b { color: var(--accent); }
.error { color: var(--danger); font-size: 13px; }

.toolbar { display: flex; justify-content: space-between; padding: 12px 24px; border-bottom: 1px solid var(--border-color); flex-shrink: 0; gap: 12px; flex-wrap: wrap; }
.filters, .sort-group, .search-group { display: flex; gap: 4px; align-items: center; }
.search-group .search-input {
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
  border-radius: 5px;
  font-size: 12px;
  width: 140px;
  outline: none;
}
.search-group .search-input:focus { border-color: var(--accent); }
.search-group .search-input::placeholder { color: var(--text-muted); }
.fbtn { padding: 4px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-secondary); border-radius: 5px; font-size: 12px; cursor: pointer; transition: all 200ms; white-space: nowrap; }
.fbtn:hover { color: var(--text-primary); border-color: var(--text-muted); }
.fbtn.active { background: var(--accent); color: #121212; border-color: var(--accent); }

.rating-list { flex: 1; padding: 0 24px 24px; }
.list-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; position: sticky; top: 0; background: var(--bg-primary); z-index: 10; }
.list-header h3 { font-family: 'Righteous', sans-serif; font-size: 18px; color: var(--accent); }
.count { font-weight: 400; font-size: 14px; color: var(--text-muted); }
.pager { display: flex; gap: 8px; align-items: center; font-size: 13px; color: var(--text-secondary); }
.pager button { padding: 4px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary); border-radius: 4px; cursor: pointer; }
.pager button:disabled { opacity: 0.3; cursor: default; }

.cards { display: flex; flex-direction: column; gap: 6px; }
.card { display: flex; justify-content: space-between; align-items: flex-start; padding: 14px 16px; background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color); transition: border-color 200ms; }
.card:hover { border-color: var(--text-muted); }
.card-left { display: flex; flex-direction: column; gap: 4px; }
.title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.title-link { font-size: 14px; font-weight: 600; color: var(--text-primary); text-decoration: none; transition: color 150ms; }
.title-link:hover { color: var(--accent); text-decoration: underline; }
.meta { font-size: 12px; color: var(--text-muted); }
.review { font-size: 12px; color: var(--text-secondary); font-style: italic; margin-top: 2px; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
.stars { font-size: 14px; letter-spacing: 1px; }
.date { font-size: 11px; color: var(--text-muted); }
.actions { display: flex; gap: 4px; margin-top: 4px; }
.act-btn { background: none; border: 1px solid var(--border-color); color: var(--text-muted); font-size: 12px; padding: 2px 8px; border-radius: 4px; cursor: pointer; transition: all 150ms; }
.act-btn:hover { color: var(--accent); border-color: var(--accent); }
.act-btn.del:hover { color: var(--danger); border-color: var(--danger); }

.edit-row { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 12px; }
.edit-controls { display: flex; gap: 8px; align-items: center; }
.edit-select { padding: 4px 8px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary); border-radius: 4px; font-size: 13px; }
.edit-input { padding: 4px 8px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary); border-radius: 4px; font-size: 13px; width: 200px; outline: none; }
.edit-input:focus { border-color: var(--accent); }
.save-btn { padding: 4px 12px; background: var(--accent); color: #121212; border: none; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; }
.cancel-btn { padding: 4px 12px; background: transparent; color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: 4px; font-size: 12px; cursor: pointer; }

.loading { text-align: center; padding: 40px; color: var(--text-muted); }
.empty { text-align: center; padding: 60px 20px; color: var(--text-muted); font-size: 14px; }
</style>
