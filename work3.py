import redis
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class TaskWorker:
    """Redis任务队列处理器，负责从队列获取任务并存储处理结果"""

    def __init__(self):
        """初始化Redis连接配置"""
        self.REDIS_CONN_PARAM = {
            "host": "127.0.0.1",
            "password": "123456",
            "port": 6379,
            "encoding": "utf8",
            "decode_responses": True
        }
        self.conn = redis.Redis(**self.REDIS_CONN_PARAM)

    def get_task(self):
        """从spire_task_list队列阻塞获取任务
        返回: 成功返回任务字典，失败返回None
        """
        try:
            data = self.conn.brpop("spire_task_list", timeout=10)
            if not data:
                return None
            return json.loads(data[1])
        except Exception as e:
            print(f"[ERROR]获取任务出错:{e}")
            return None

    def set_result(self, task_id, status, result=None):
        """将任务结果存入spire_task_list_result队列
        参数:
            task_id: 任务唯一标识
            status: 任务状态(成功/失败)
            result: 任务执行结果(可选)
        """
        try:
            result_data = {"tid": task_id, "status": status, "result": result}
            self.conn.lpush("spire_task_list_result", json.dumps(result_data))
        except Exception as e:
            print(f"[ERROR]存储结果出错:{e}")

    def fetch_rate_data(self):
        """使用Selenium获取汇率数据"""
        driver = webdriver.Chrome(service=Service(executable_path="D:/chromedriver/chromedriver.exe"))
        driver.maximize_window()
        driver.get("https://gushitong.baidu.com/?quotationMarket=foreign&moduleName=quotation")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "all-stock")))
        driver.find_element(By.CSS_SELECTOR,
                            'div.page-module.page-module-blocks > div > div:nth-child(1) > div > div > div.santd-tabs-content.santd-tabs-top-content.santd-tabs-content-no-animated > div.santd-tabs-tabpane.santd-tabs-tabpane-active > div > div > div > div.more-wrapper.c-font-normal.more-text > span').click()

        current_list = ["美元", "人民币"]
        data_list = []
        for currency in current_list:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.HOME)
            xpath = f"//div[text()='{currency}']"
            try:
                element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                if "active" not in element.get_attribute("class"):
                    element.click()
                else:
                    print(f"{currency} 已是当前状态")
            except TimeoutException:
                print(f"切换失败：{currency} 元素未找到或不可操作")

            max_attempts = 20
            scroll_pause_time = 2
            for attempt in range(max_attempts):
                try:
                    end_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[text()='到底了...']")))
                    print("检测到结束标记，停止滚动")
                    break
                except (NoSuchElementException, TimeoutException):
                    print(f"第 {attempt + 1} 次滚动...")
                    body = driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.END)
                    driver.implicitly_wait(scroll_pause_time)

            if attempt == max_attempts - 1:
                print(f"已达最大尝试次数 {max_attempts} 次，未检测到结束标记")
            else:
                print("正常退出循环")

            list_items = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list-item.finance-hover")))
            for item in list_items:
                try:
                    name = item.find_element(By.CSS_SELECTOR, "div.name.c-color").text
                except NoSuchElementException:
                    name = "N/A"
                try:
                    code = item.find_element(By.CSS_SELECTOR, "span.code.c-gap-left-lh").text
                except NoSuchElementException:
                    code = "N/A"
                try:
                    market_label = item.find_element(By.CSS_SELECTOR, "path#FX").get_attribute("fill")
                    market = "外汇" if market_label == "#7C1EFF" else "其他"
                except NoSuchElementException:
                    market = "N/A"
                try:
                    data_id = item.get_attribute("data-id")
                except NoSuchElementException:
                    data_id = "N/A"
                data = {"名称": name, "代码": code, "市场类型": market, "data-id": data_id}
                data_list.append(data)

        driver.quit()
        return data_list

    def process_task(self, task):
        """实际任务处理逻辑
        参数:
            task: 包含任务数据的字典
        返回:
            任务处理结果
        """
        print(f"[PROCESS]正在处理任务:{task}")
        result = self.fetch_rate_data()
        return {"input": task, "output": result}

    def run(self):
        """主循环，持续处理任务队列"""
        print("[SYSTEM]任务处理器启动...")
        while True:
            task = self.get_task()
            if not task:
                continue
            try:
                print(f"[TASK]开始处理任务ID:{task.get('tid')}")
                result = self.process_task(task)
                self.set_result(task['tid'], "SUCCESS", result)
                print(f"[TASK]任务{task['tid']}处理完成")
            except Exception as e:
                print(f"[ERROR]任务{task.get('tid')}处理失败:{e}")
                self.set_result(task['tid'], "FAILED", str(e))


if __name__ == '__main__':
    worker = TaskWorker()
    worker.run()
