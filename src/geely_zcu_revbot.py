import os
import pickle
from configs.config import LIB_PATH
from collections import defaultdict

from src.RevBot import AICodeReviewOrchestrator


class GeelyZCU(AICodeReviewOrchestrator):
    def _get_checklist_table(self):
        markdown_table = '''
***<ins>This checklist must to be filled by SWD before submit code review and checked by SWA during code review!!!<ins>***

To successfully close a review, all questions in this checklist are required to be marked with one of the options listed.

- Questions marked as NOK, the reason shall be documented.
- Questions marked as N/A (Not Applicable), the justification shall be documented (if the reason is not clear).
- Checklist is mandatory for walkthrough / inspection and recommended for peer review

<table id="user-content-code_review_checks_table" role="table">
<tbody><tr>
<td align="center"><b>Id</b></td>
<td><b>Question</b></td>
<td align="left">✅ OK <br> ❌ NOK<br> ❔ N/A</td>
<td align="center">Comment<a target="_blank" rel="noopener noreferrer" href=""><img width="200/" style="max-width: 100%;"></a></td>
</tr>
<tr>
<td align="center"><b>1</b></td>
<td>
Are all shared variables (global,  Function and file scoped static variables) used in different preemptive tasks (interrupt, preemptive tasks from the scheduler) or hardware register declared as volatile? (To avoid unexpected optimization)?

<B>Yes => OK</B>

<i>If volatile is not used for good reason, put Nok and justify.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>

<td>  </td>
</tr>
<tr>
<td align="center"><b>2</b></td>
<td>
Are all individual or group of coherent shared variables protected to avoid access conflicts?

<B>Yes => OK</B>

<i>If volatile is not used for good reason, put Nok and justify.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>3</b></td>
<td>
Is the exit condition of each loop robust? Does each loop waiting for an event have an alternate escape mechanism? (time-out, ...)?

 <B>Yes => OK</B>

<i>E.g. while(SPI_DONE == FALSE) { ... } /* not OK – infinite if any communication error */</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>4</b></td>
<td>
Are there any multiple assignments in the same expression?

<B>NO=>OK</B>

<i>expressions like a=b=c; are not OK</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>5</b></td>
<td>
Is there any bit fields access of a larger data type which relies on the way that the bit fields are stored?

<B>NO=>OK</B>

<i>For example splitting a word in high and low bytes based on struct unions. Only the usage of standard T_FLAG8, T_FLAG16 is allowed for this purposes.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>6</b></td>
<td>
Is there any pointer arithmetic applied to pointers which do not address an array or an array element?

<B>NO=>OK</B>

<i>Pointer arithmetic is allowed only for array indexing purposes.

Reference: ISO 26262-6:2018 chapter 8.4.5 table 6.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>7</b></td>
<td>
Is there any assignment or memory copy operation of overlapping objects or memory areas/regions?

<B>NO=>OK</B>

<i>E.g.: memcpy( &array[1], &array[4], 8 ); /* destination and source overlap  - array type uint8*/

Reference: ISO 26262-6:2018 chapter 8.4.5 table 6.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>8</b></td>
<td>
Is each macro/function-call which disables interrupts (e.g. ENTER_PROTECTED_SECTION, SuspendAllInterrupts()) followed by restoring the previous level (e.g. LEAVE_PROTECTED_SECTION, ResumeAllInterrupts()) in all cases?

<B>YES=>OK</B>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>9</b></td>
<td>
Are all interrupts acknowledged in all paths of the ISR?

<B>YES=>OK</B>

<i>On certain platforms (e.g. v850 FX3) "interrupt acknowledgement" is done automatically by HW when ISR is launched into execution.
However on other platforms (e.g. HC12, S12x etc) "interrupt acknowledgement" has to be done explicitly in code.
</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>10</b></td>
<td>
Are there any assertions in code which might have side effects?

<B>NO=>OK</B>

<i>Assertions shall be used only to detect internal software errors.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>11</b></td>
<td>
Are there any assertions checking for conditions that must be handled in production code?

<B>NO=>OK</B>

<i>Assertions shall be used only to detect internal software errors.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>12</b></td>
<td>
Are there static local variable defined?

<B>NO=>OK</B>

<i>The reasons are:
- You cannot assign a local static variable to a specific memory section
- A local static variable cannot be reinitialized
- Testability - you cannot access this variable from your module test code. It means, if i.e. such a variable is state variable, you cannot test this state machine using module test.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>13</b></td>
<td>
Are all variables allocated specific section appropriately initialized?

<B>YES=>OK</B>

<i><i>Refer to [Part 2 of Uncacheable variables and rules](https://confluence.auto.continental.cloud/pages/viewpage.action?pageId=1977025208#UncacheableVariableMemorySection-Part2)</i></i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>14</b></td>
<td>
Are all variables which cannot be cached declared in the VAR_CLEARED_NO_CACHEABLE or VAR_INIT__NO_CACHEABLE sections.

<B>YES=>OK</B>

<i>Refer to [Part 1 of Uncacheable variables and rules](https://confluence.auto.continental.cloud/pages/viewpage.action?pageId=1977025208#UncacheableVariableMemorySection-Part1)</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>


<td>  </td>
</tr>
<tr>
<td align="center"><b>15</b></td>
<td>
Does files_properties.xml updated for the new added code files(.h, .c, .cpp) to avoid N/A in SCCE?

<B>YES=>OK</B>

<i>if no new code files added, put as YES.</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>

<td>  </td>
</tr>
<tr>
<td align="center"><b>16</b></td>
<td>
Is there any data buffer/array in the submitted code that needs to determine the boundary? Is the determination made explicitly in the code?

<B>YES=>OK</B>

</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>

<td>  </td>
</tr>
<tr>
<td align="center"><b>17</b></td>
<td>
Have checklists for updating <B>variants/ZCUDX/cfg/ParamAppl/Parameter.xlsx</B> and <B>variants/ZCUDX/cfg/ParamAppl/Parameter.csv</B> been done?

<B>YES=>OK</B>

<i>The parameter checklists:
- Is the parameters mentioned in the current ticket have been modified and their values have been validated?
- Is the parameters unrelated to this ticket have not been modified or uploaded?
- Is the CSV file generated correctly, and the all differences have been reviewed?</i>

<i>Refer to [DCU and SCU parameter management](https://confluence.auto.continental.cloud/display/SPACE2285/13+DCU+and+SCU+parameter+management)</i>
</td>
<td nowrap="">
⬜ OK<br>⬜ NOK<br>⬜ N/A
</td>

<td>  </td>
</tr>
</tbody></table>
        '''

        return markdown_table
    
    def _get_prompt(self, ticket_detail, base_branch, repo, diff_content, language='zh'):

        rule_descriptions = self._build_rules_prompt(language=language)

        if language == 'zh':
            review_instruction = (
                "# 以下修改属于汽车嵌入式软件开发项目，请根据 Jira 需求和对应的 Github Pull Request 变更进行代码审查，并评估合并风险。\n"
                "## 审查要求：\n"
                "1. 必须用中文回答。\n"
                "2. 对发现的问题可适当提供修改建议。\n"
                "3. 必须对每个文件检查以下代码规范并指出违反之处，必须以表格的方式呈现，必须在表格前和表格后空行，表格的列包括：Code Rules | Comments：\n"
                "   - MISRA_2012\n"
                "   - CERT_C_2016\n"
                "4. 若代码中包含以下格式的注释：\n"
                "   /* ANALYSIS_REPORT_JUSTIFICATION (...) !--> TOOL_NUMBER(...) GUIDELINE(...) ... <--! */\n"
                "   则根据 /* GUIDELINE(...) ... */ 中的特殊规则来审核相关代码。\n"
                "5. 以下的字典包含了某些文件的特殊审核规则，若修改的文件或者文件路径出现在如下的字典中，请参考与其对应的代码特殊规则及对应的章节：\n"
                f"{rule_descriptions}\n"
                "6. 如果发现某些修改在规范、标准或技术知识方面存在明显欠缺，请在审查意见中提供相关资料或官方文档链接，帮助开发者补齐知识短板。\n"
                "7. 输出结果必须严格按照以下结构组织：\n"
                "   **1. 总体评价**：对整体代码质量、规范符合度、潜在风险进行综合评价。\n"
                "   **2. 逐一文件建议和分析**：按文件逐个分析变更内容，指出问题、规范违规情况及修改建议。\n"
                "   **3. 总结**：总结主要发现、风险等级及后续建议。\n"
                "   **4. Checklist**：使用下方提供的检查项，按表格格式填写。\n"
                "   **5. 合并风险评估**：在最后一行只输出一个单词字符表示风险等级（low / medium / high），不要有解释或额外内容。\n"
            )

            checklist_instruction = (
                """
                请根据以下代码审查检查项（Checklist）对 Github Pull Request 变更的代码进行逐项检查，并以表格形式返回结果。

                【输出格式要求】：
                - 每一行对应一个检查项
                - 列包括：Checklist Item No. | Checklist Descriptions | Status (OK / NOK / N/A) | Comments
                - 当 Status 为 NOK 或 N/A 时，必须在 Comments 中写明原因或说明，并加粗Status的NOK 或 N/A
                - 当 Status 为 OK 时，Comments 留空

                【检查项列表】：
                1. Are all shared variables (global, Function and file scoped static variables) used in different preemptive tasks (interrupt, preemptive tasks from the scheduler) or hardware register declared as volatile? (To avoid unexpected optimization)?  
                    Yes => OK  
                    If volatile is not used for good reason, put NOK and justify.

                2. Are all individual or group of coherent shared variables protected to avoid access conflicts?  
                    Yes => OK  
                    If volatile is not used for good reason, put NOK and justify.

                3. Is the exit condition of each loop robust? Does each loop waiting for an event have an alternate escape mechanism (time-out, ...)?  
                    Yes => OK  
                    E.g. while(SPI_DONE == FALSE) { ... } /* not OK – infinite if any communication error */

                4. Are there any multiple assignments in the same expression?  
                    NO => OK  
                    Expressions like a = b = c; are not OK.

                5. Is there any bit fields access of a larger data type which relies on the way that the bit fields are stored?
                    NO => OK  
                    For example splitting a word in high and low bytes based on struct unions. Only the usage of standard T_FLAG8, T_FLAG16 is allowed for this purposes.

                6. Is there any pointer arithmetic applied to pointers which do not address an array or an array element?
                    NO => OK  
                    Pointer arithmetic is allowed only for array indexing purposes.
                    Reference: ISO 26262-6:2018 chapter 8.4.5 table 6.

                7. Is there any assignment or memory copy operation of overlapping objects or memory areas/regions?
                    NO => OK  
                    E.g.: memcpy(&array[1], &array[4], 8); /* destination and source overlap */  
                    Reference: ISO 26262-6:2018 chapter 8.4.5 table 6.

                8. Is each macro/function-call which disables interrupts (e.g. ENTER_PROTECTED_SECTION, SuspendAllInterrupts()) followed by restoring the previous level (e.g. LEAVE_PROTECTED_SECTION, ResumeAllInterrupts()) in all cases?
                    YES => OK

                9. Are all interrupts acknowledged in all paths of the ISR?
                    YES => OK
                    On certain platforms (e.g. v850 FX3) "interrupt acknowledgement" is done automatically by HW when ISR is launched into execution. However on other platforms (e.g. HC12, S12x etc) "interrupt acknowledgement" has to be done explicitly in code.

                10. Are there any assertions in code which might have side effects?
                    NO => OK
                    Assertions shall be used only to detect internal software errors.

                11. Are there any assertions checking for conditions that must be handled in production code?
                    NO => OK
                    Assertions shall be used only to detect internal software errors.
                    
                12. Are there static local variables defined?  
                    NO => OK
                    
                    The reasons are:
                    1. You cannot assign a local static variable to a specific memory section
                    2. A local static variable cannot be reinitialized
                    3. Testability - you cannot access this variable from your module test code. It means, if i.e. such a variable is state variable, you cannot test this state machine using module test.

                13. Are all variables allocated specific section appropriately initialized?  
                    YES => OK

                14. Are all variables which cannot be cached declared in the VAR_CLEARED_NO_CACHEABLE or VAR_INIT_NO_CACHEABLE sections?  
                    YES => OK

                15. Does files_properties.xml updated for the new added code files (.h, .c, .cpp) to avoid N/A in SCCE?  
                    YES => OK  
                    If no new code files added, put as YES.

                16. Is there any data buffer/array in the submitted code that needs to determine the boundary? Is the determination made explicitly in the code?  
                    YES => OK

                17. Have checklists for updating variants/ZCUDX/cfg/ParamAppl/Parameter.xlsx and variants/ZCUDX/cfg/ParamAppl/Parameter.csv been done?
                    YES => OK

                    The parameter checklists:
                    1. Is the parameters mentioned in the current ticket have been modified and their values have been validated?
                    2. Is the parameters unrelated to this ticket have not been modified or uploaded?
                    3. Is the CSV file generated correctly, and the all differences have been reviewed?

                【最终输出示例】：
                Checklist Item No. | Checklist | Status | Comments
                1 | Are all shared variables (global, function and file scoped static variables) used in different preemptive tasks (interrupt, preemptive tasks from the scheduler) or hardware register declared as volatile? (To avoid unexpected optimization)?  Yes => OK  If volatile is not used for good reason, put NOK and justify. | OK | 
                2 | Are all individual or group of coherent shared variables protected to avoid access conflicts?  Yes => OK | NOK | Missing mutex protection for shared variable 'g_dataBuffer'
                3 | ... | OK |
                4 | ... | OK |
                5 | ... | N/A | No bit field access detected in submitted code
                ...
                """
            )

            merge_instruction = (
                "## 合并风险评估规则：\n"
                "- low：代码规范好，变更范围小，无明显风险。\n"
                "- medium：存在少量规范问题或潜在风险，但可以接受。\n"
                "- high：存在严重规范问题、潜在错误或设计缺陷，不建议直接合并。\n"
                "请根据你的整体分析，**在最终一行只输出一个单词字符作为合并风险结果（low / medium / high）**，不要输出多余内容或解释。"
            )

            question = (
                f"{review_instruction}\n"
                f"# 本次变更的 Jira 需求：\n{ticket_detail or '无'}\n\n"
                f"# 本次变更的目标分支：\n{base_branch}\n\n"
                f"# 仓库 {repo} 的 Pull Request 变更内容如下：\n{diff_content}\n\n"
                f"{checklist_instruction}\n\n"
                f"{merge_instruction}"
            )

        else:
            review_instruction = (
                "# The following changes belong to the automotive embedded software development project. Please review the code based on the Jira requirements and the corresponding Github Pull Request changes, and assess the merge risk.\n"
                "## Review Requirements:\n"
                "1. Must answer in English.\n"
                "2. Provide modification suggestions for identified issues.\n"
                "3. Check each file for compliance with the following code standards and point out violations in a tabular format, with a blank line before and after the table. The columns should include: Code Rules | Comments:\n"
                "   - MISRA_2012\n"
                "   - CERT_C_2016\n"
                "4. If the code contains comments in the following format:\n"
                "   /* ANALYSIS_REPORT_JUSTIFICATION (...) !--> TOOL_NUMBER(...) GUIDELINE(...) ... <--! */\n"
                "   then based on the speical review rules in /* GUIDELINE(...) ... */ to review the rervelant codes.\n"
                "5. The following dictionary contains special review rules for certain files. If the modified files or files path appear in the following dictionary, please refer to the special rules and chapters corresponding to them:\n"
                f"{rule_descriptions}\n"
                "6. If you find that some changes have obvious shortcomings in terms of standards, specifications, or technical knowledge, please provide relevant materials or official document links in your review comments to help developers fill in knowledge gaps.\n"
                "7. The output must be strictly organized according to the following structure:\n"
                "   **1. Overall Evaluation**: A comprehensive evaluation of overall code quality, compliance with standards, and potential risks.\n"
                "   **2. File-by-File Suggestions and Analysis**: Analyze changes file by file, pointing out issues, standard violations, and modification suggestions.\n"
                "   **3. Summary**: Summarize main findings, risk levels, and follow-up recommendations.\n"
                "   **4. Checklist**: Use the checklist provided below and fill it out in tabular format.\n"
                "   **5. Merge Risk Assessment**: At the very last line, output only one word character representing the risk level (low / medium / high), without explanations or additional content.\n"
            )

            checklist_instruction = (
                """
                Please review the Github Pull Request changes according to the following code review checklist, and return the results in a table format.

                [Output Format Requirements]:
                - Each row corresponds to one checklist item
                - Columns include: Checklist Item No. | Checklist Descriptions | Status (OK / NOK / N/A) | Comments
                - When Status is NOK or N/A, you must specify the reason or explanation in Comments, and **bold** the Status NOK or N/A
                - When Status is OK, leave Comments blank

                [Checklist Items]:
                1. Are all shared variables (global, function and file scoped static variables) used in different preemptive tasks (interrupt, preemptive tasks from the scheduler) or hardware registers declared as volatile? (To avoid unexpected optimization)?  
                    Yes => OK  
                    If volatile is not used for good reason, put NOK and justify.

                2. Are all individual or groups of coherent shared variables protected to avoid access conflicts?  
                    Yes => OK  
                    If volatile is not used for good reason, put NOK and justify.

                3. Is the exit condition of each loop robust? Does each loop waiting for an event have an alternate escape mechanism (timeout, ...)?  
                    Yes => OK  
                    E.g. while(SPI_DONE == FALSE) { ... } /* not OK – infinite if any communication error */

                4. Are there any multiple assignments in the same expression?  
                    NO => OK  
                    Expressions like a = b = c; are not OK.

                5. Is there any bit field access of a larger data type which relies on the way that the bit fields are stored?
                    NO => OK  
                    For example, splitting a word into high and low bytes based on struct unions. Only the usage of standard T_FLAG8, T_FLAG16 is allowed for these purposes.

                6. Is there any pointer arithmetic applied to pointers which do not address an array or an array element?
                    NO => OK  
                    Pointer arithmetic is allowed only for array indexing purposes.
                    Reference: ISO 26262-6:2018 chapter 8.4.5 table 6.

                7. Is there any assignment or memory copy operation of overlapping objects or memory areas/regions?
                    NO => OK  
                    E.g.: memcpy(&array[1], &array[4], 8); /* destination and source overlap */  
                    Reference: ISO 26262-6:2018 chapter 8.4.5 table 6.

                8. Is each macro/function-call which disables interrupts (e.g. ENTER_PROTECTED_SECTION, SuspendAllInterrupts()) followed by restoring the previous level (e.g. LEAVE_PROTECTED_SECTION, ResumeAllInterrupts()) in all cases?
                    YES => OK

                9. Are all interrupts acknowledged in all paths of the ISR?
                    YES => OK
                    On certain platforms (e.g. v850 FX3) "interrupt acknowledgement" is done automatically by HW when ISR is launched into execution. However, on other platforms (e.g. HC12, S12x etc) "interrupt acknowledgement" has to be done explicitly in code.

                10. Are there any assertions in code which might have side effects?
                    NO => OK
                    Assertions shall be used only to detect internal software errors.

                11. Are there any assertions checking for conditions that must be handled in production code?
                    NO => OK
                    Assertions shall be used only to detect internal software errors.
                    
                12. Are there static local variables defined?  
                    NO => OK
                    
                    The reasons are:
                    1. You cannot assign a local static variable to a specific memory section
                    2. A local static variable cannot be reinitialized
                    3. Testability - you cannot access this variable from your module test code. It means, if such a variable is a state variable, you cannot test this state machine using module test.

                13. Are all variables allocated to specific sections appropriately initialized?  
                    YES => OK

                14. Are all variables which cannot be cached declared in the VAR_CLEARED_NO_CACHEABLE or VAR_INIT_NO_CACHEABLE sections?  
                    YES => OK

                15. Is files_properties.xml updated for the newly added code files (.h, .c, .cpp) to avoid N/A in SCCE?  
                    YES => OK  
                    If no new code files added, put YES.

                16. Is there any data buffer/array in the submitted code that needs boundary determination? Is the determination made explicitly in the code?  
                    YES => OK

                17. Have checklists for updating variants/ZCUDX/cfg/ParamAppl/Parameter.xlsx and variants/ZCUDX/cfg/ParamAppl/Parameter.csv been completed?
                    YES => OK

                    The parameter checklists:
                    1. Have the parameters mentioned in the current ticket been modified and their values validated?
                    2. Have parameters unrelated to this ticket not been modified or uploaded?
                    3. Is the CSV file generated correctly, and have all differences been reviewed?

                [Final Output Example]:
                Checklist Item No. | Checklist | Status | Comments
                1 | Are all shared variables (global, function and file scoped static variables) used in different preemptive tasks (interrupt, preemptive tasks from the scheduler) or hardware register declared as volatile? (To avoid unexpected optimization)?  Yes => OK  If volatile is not used for good reason, put NOK and justify. | OK | 
                2 | Are all individual or group of coherent shared variables protected to avoid access conflicts?  Yes => OK | NOK | Missing mutex protection for shared variable 'g_dataBuffer'
                3 | ... | OK |
                4 | ... | OK |
                5 | ... | N/A | No bit field access detected in submitted code
                ...
                """
            )

            merge_instruction = (
                "## Merge Risk Assessment Rules:\n"
                "- low: Code is well standardized, changes are minor, no obvious risks.\n"
                "- medium: There are a few standard issues or potential risks, but they are acceptable.\n"
                "- high: There are serious standard issues, potential errors, or design flaws. Direct merging is not recommended.\n"
                "Based on your overall analysis, **output only one word character as the merge risk result (low / medium / high) in the final line**, do not output extra content or explanations."
            )

            question = (
                f"{review_instruction}\n"
                f"# Jira requirement for this change:\n{ticket_detail or 'None'}\n\n"
                f"# Target branch for this change:\n{base_branch}\n\n"
                f"# Pull Request changes for repository {repo} are as follows:\n{diff_content}\n\n"
                f"{checklist_instruction}\n\n"
                f"{merge_instruction}"
            )
        
        return question
    
    def _get_qtools_result_filter(self, changed_files, owner, repo):

        file_names = [os.path.basename(path) for path in changed_files] + ['*']

        qtools_filter_path = os.path.join(LIB_PATH, owner, 'qtools', repo) + '.pkl'

        filtered_rules = {}

        if os.path.exists(qtools_filter_path):
            with open(qtools_filter_path, 'rb') as f:
                loaded_rules = pickle.load(f)

            for file_name in file_names:
                if file_name in loaded_rules:
                    filtered_rules[file_name] = {
                        'code_rules': loaded_rules[file_name]['code_rules'],
                        'code_rule_chapters': loaded_rules[file_name]['code_rule_chapters'],
                        'descriptions': loaded_rules[file_name]['descriptions']
                    }


        return filtered_rules

    def _build_rules_prompt(self, language):
        lines = []

        if language == 'zh':
            
            for filename, rule_info in self.rule_descriptions.items():

                lines.append(f"文件：{filename}")

                for code_rule, chapter in zip(rule_info.get('code_rules', []), rule_info.get('code_rule_chapters', [])):
                    lines.append(f"  规则编号: {code_rule}，章节: {chapter}")

                for desc in rule_info.get('descriptions', []):
                    lines.append(f"  说明: {desc}")

                lines.append("")

        else:

            for filename, rule_info in self.rule_descriptions.items():

                lines.append(f"File: {filename}")

                for code_rule, chapter in zip(rule_info.get('code_rules', []), rule_info.get('code_rule_chapters', [])):
                    lines.append(f"  Code Rules: {code_rule}, Code Rules Chapters: {chapter}")

                for desc in rule_info.get('descriptions', []):
                    lines.append(f"  Descriptions: {desc}")

                lines.append("")

        rule_descriptions = "\n".join(lines)
        return rule_descriptions
    

    def _get_ut(self, changed_files, owner, repo):

        file_names = [os.path.basename(path) for path in changed_files]

        ut_path = os.path.join(LIB_PATH, owner, 'ut', repo)

        for file_name in file_names:
            file_path = os.path.join(ut_path, file_name) + '.test'
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
